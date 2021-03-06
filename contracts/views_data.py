import json
from django.db.models import Count
from django.http import HttpResponse
import analysis
from django.core.cache import cache


def get_entities_categories_ranking(flush_cache=False):
    cache_name = 'entities_categories_ranking'

    entities = cache.get(cache_name)
    if entities is None or flush_cache:
        entities = analysis.get_ranking()
        entities = entities.annotate(contracts_number=Count('contracts_made__id'))
        entities = list(entities)
        cache.set(cache_name, entities, 60*60*48)

    return entities


def entities_category_ranking_json(request):
    data = []
    count = 0
    for entity in get_entities_categories_ranking():
        count += 1
        name = entity.name.split(' ')[2:]
        name = ' '.join(name)
        data.append({'name': name, 'rank': count, 'avg_depth': entity.avg_depth})

    return HttpResponse(json.dumps(data), content_type="application/json")


def entities_category_ranking_histogram_json(request):

    entities = get_entities_categories_ranking()

    min_value = entities[-1].avg_depth - 0.00000001  # avoid rounding, this caused a bug before.
    max_value = entities[0].avg_depth + 0.00000001   # avoid rounding, this caused a bug before.
    n_bins = 20

    # center between max and min: min_value + (max_value - min_value)*(count)/n_bins + (max_value - min_value)/n_bins/2

    # create the histogram
    data = [{'bin': x,
             'value': 0,
             'min_position': min_value + (max_value - min_value)*x/n_bins,
             'max_position': min_value + (max_value - min_value)*(x+1)/n_bins
            } for x in range(n_bins)]

    for entity in entities:
        for x in range(n_bins):
            if data[x]['min_position'] < entity.avg_depth <= data[x]['max_position']:
                data[x]['value'] += 1
                break

    return HttpResponse(json.dumps(data), content_type="application/json")


def get_contracts_price_distribution(flush_cache=False):
    cache_name = 'contracts_price_distribution'

    distribution = cache.get(cache_name)
    if distribution is None or flush_cache:
        distribution = analysis.get_price_histogram()
        cache.set(cache_name, distribution, 60*60*24)

    return distribution


def contracts_price_histogram_json(request):

    distribution = get_contracts_price_distribution()

    data = []
    for entry in distribution:
        if entry[1]:
            data.append({'min_position': entry[0],
                         'max_position': entry[0]*2,
                         'value': entry[1]})

    return HttpResponse(json.dumps(data), content_type="application/json")


def get_contracts_macro_statistics(flush_cache=False):
    cache_name = 'contract_prices'

    values = cache.get(cache_name)
    if values is None or flush_cache:
        values = analysis.get_contracts_macro_statistics()
        cache.set(cache_name, values, 60*60*48)

    return values


def contracts_macro_statistics_json(request):
    data = get_contracts_macro_statistics()
    return HttpResponse(json.dumps(data), content_type="application/json")
