from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Sum, Count
from treebeard.ns_tree import NS_Node


class Country(models.Model):
    name = models.CharField(max_length=254)


class District(models.Model):
    name = models.CharField(max_length=254)

    base_id = models.IntegerField(unique=True)

    country = models.ForeignKey('Country')


class CPVS(models.Model):
    code = models.CharField(max_length=254)
    description_en = models.CharField(max_length=254)
    description_pt = models.CharField(max_length=254)

    def division(self):
        return CPVS.objects.get(code__startswith=self.code[:2] + '000000-')

    def group(self):
        return CPVS.objects.get(code__startswith=self.code[:3] + '00000-')

    def klass(self):
        return CPVS.objects.get(code__startswith=self.code[:4] + '0000-')

    def category(self):
        return CPVS.objects.get(code__startswith=self.code[:5] + '000-')

    def sub_category1(self):
        return CPVS.objects.get(code__startswith=self.code[:6] + '00-')

    @classmethod
    def divisions(cls):
        return CPVS.objects.filter(code__contains='000000-')

    def groups(self):
        return CPVS.objects.filter(code__startswith=self.code[:2], code__contains='00000-').exclude(pk=self.pk)

    def classes(self):
        return CPVS.objects.filter(code__startswith=self.code[:3], code__contains='0000-').exclude(pk=self.pk)

    def categories(self):
        return CPVS.objects.filter(code__startswith=self.code[:4], code__contains='000-').exclude(pk=self.pk)

    def sub_categories1(self):
        return CPVS.objects.filter(code__startswith=self.code[:5], code__contains='00-').exclude(pk=self.pk)

    def sub_categories2(self):
        return CPVS.objects.filter(code__startswith=self.code[:6], code__contains='0-').exclude(pk=self.pk)

    def sub_categories3(self):
        return CPVS.objects.filter(code__startswith=self.code[:7]).exclude(pk=self.pk)

    def __unicode__(self):
        return self.code[:8]


class Category(NS_Node):
    code = models.CharField(max_length=254)
    description_en = models.CharField(max_length=254)
    description_pt = models.CharField(max_length=254)

    def __unicode__(self):
        return '%s' % self.code[:8]

    def get_absolute_url(self):
        return reverse('category_view', args=[self.pk])

    def _own_contracts_aggregate(self):
        cache_name = __name__ + '>_own_contracts_aggregate' + '>%s' % self.code
        aggregate = cache.get(cache_name)
        if aggregate is None:
            aggregate = dict(self.contract_set.aggregate(Sum('price'), Count('price')))
            cache.set(cache_name, aggregate, 60*60*24)
        return aggregate

    def own_contracts_count(self):
        return self._own_contracts_aggregate()['price__count']

    def own_contracts_price(self):
        return self._own_contracts_aggregate()['price__sum']

    def contracts(self):
        return Contract.objects.filter(cpvs__startswith='%s' % self.code[:self.depth + 1])

    def _contracts_aggregate(self):
        cache_name = __name__ + '>_contracts_aggregate' + '>%s' % self.code
        aggregate = cache.get(cache_name)
        if aggregate is None:
            aggregate = dict(self.contracts().aggregate(Sum('price'), Count('price')))
            cache.set(cache_name, aggregate, 60*60*24)

        return aggregate

    def contracts_count(self):
        return self._contracts_aggregate()['price__count']

    def contracts_price(self):
        return self._contracts_aggregate()['price__sum']


class Council(models.Model):

    name = models.CharField(max_length=254)

    base_id = models.IntegerField()

    district = models.ForeignKey('District')


class Entity(models.Model):

    name = models.CharField(max_length=254)

    base_id = models.IntegerField(unique=True)

    nif = models.CharField(max_length=254)

    country = models.ForeignKey('Country', null=True)

    def total_earned(self):
        return self.data.total_earned

    def total_expended(self):
        return self.data.total_expended

    def last_contract_date(self):
        try:
            #return Contract.objects.filter(Q(contracted__pk=self.id) | Q(contractors__pk=self.id)).order_by('-signing_date')[0]
            pass
        except IndexError:
            return None

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return 'http://www.base.gov.pt/base2/html/pesquisas/entidades.shtml#%s' % self.base_id

    def count_contracts(self):
        return self.contracts_made.count()

    def add_contract_as_contracted(self, contract):
        self.data.total_earned += contract.price
        self.data.save()

    def add_contract_as_contractor(self, contract):
        self.data.total_expended += contract.price
        self.data.save()

    def compute_data(self):
        """
        Computes the data of this entity from the existing relations.
        """
        print 'computing data of entity %d' % self.base_id

        # if data does not exist, we create it.
        try:
            self.data
        except EntityData.DoesNotExist:
            self.data = EntityData(entity=self)

        # we update the total earnings and total expenses.
        self.data.total_earned = self.contract_set.aggregate(Sum('price'))['price__sum'] or 0
        self.data.total_expended = self.contracts_made.aggregate(Sum('price'))['price__sum'] or 0
        self.data.save()


class EntityData(models.Model):
    """
    This is a class that contains data from a given entity.
    This data is always computed from existing relations.
    """
    entity = models.OneToOneField('Entity', related_name='data')
    total_earned = models.BigIntegerField(default=0)
    total_expended = models.BigIntegerField(default=0)


class ContractType(models.Model):

    base_id = models.IntegerField(unique=True)

    name = models.CharField(max_length=254)


class ProcedureType(models.Model):

    base_id = models.IntegerField(unique=True)

    name = models.CharField(max_length=254)


class Contract(models.Model):
    base_id = models.IntegerField(unique=True)
    added_date = models.DateField()
    signing_date = models.DateField(null=True)
    close_date = models.DateField(null=True)
    contract_type = models.ForeignKey('ContractType', null=True)
    procedure_type = models.ForeignKey('ProcedureType')
    description = models.TextField(null=True)
    contract_description = models.TextField()
    cpvs = models.CharField(max_length=254)
    category = models.ForeignKey('Category', null=True)
    price = models.BigIntegerField()

    country = models.ForeignKey('Country', null=True)
    district = models.ForeignKey('District', null=True)
    council = models.ForeignKey('Council', null=True)

    contractors = models.ManyToManyField('Entity', related_name='contracts_made')
    contracted = models.ManyToManyField('Entity')

    def get_absolute_url(self):
        return 'http://www.base.gov.pt/base2/html/pesquisas/contratos.shtml#%d' % self.base_id

    def get_first_entity(self):
        # there are at least two contracts with errors in the official database,
        # which leads to 0 contractors. These contracts don't have any information.
        try:
            return self.contractors.all()[0]
        except IndexError:
            return None

    class Meta:
        ordering = ['-signing_date']
