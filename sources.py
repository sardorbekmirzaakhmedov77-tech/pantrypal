"""Live recipe and cooking-guide sources. No generated recipes are passed off as search results."""
import copy
import html
import json
import os
import re
import time
from threading import Lock
from urllib.parse import urlparse
import requests

_cache={}
_lock=Lock()
class SourceError(Exception): pass

def safe_url(value):
    value=(value or '').strip()
    try:
        p=urlparse(value)
        return value if p.scheme in ('https','http') and p.hostname else ''
    except ValueError: return ''

def fetch(url,params):
    key=(url,tuple(sorted(params.items())))
    with _lock:
        hit=_cache.get(key)
        if hit and time.monotonic()-hit[0]<900: return copy.deepcopy(hit[1])
    try:
        with requests.get(url,params=params,timeout=(4,12),stream=True,headers={'User-Agent':'PantryPal/1.0 (educational recipe discovery)'}) as r:
            r.raise_for_status(); body=bytearray()
            for chunk in r.iter_content(8192):
                body.extend(chunk)
                if len(body)>3_000_000: raise SourceError('The recipe provider returned too much data. Try a more specific search.')
            data=json.loads(body)
            if not isinstance(data,dict) or data.get('error'): raise ValueError('Invalid response')
    except (requests.RequestException,ValueError) as exc:
        raise SourceError('This source is temporarily unavailable. Please try again shortly.') from exc
    with _lock:
        if len(_cache)>=150: _cache.clear()
        _cache[key]=(time.monotonic(),data)
    return copy.deepcopy(data)

def meal_url(endpoint):
    key=os.environ.get('MEALDB_API_KEY','1')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',key): raise SourceError('The recipe API key is not configured correctly.')
    return f'https://www.themealdb.com/api/json/v1/{key}/{endpoint}.php'

def normalize(m):
    key=str(m.get('idMeal',''))
    if not key.isdigit(): raise ValueError('Invalid recipe identifier')
    ingredients=[]
    for i in range(1,21):
        name=(m.get(f'strIngredient{i}') or '').strip()
        if name: ingredients.append({'name':name,'measure':(m.get(f'strMeasure{i}') or '').strip()})
    instructions=(m.get('strInstructions') or '').strip()
    # Keep source paragraphs intact; do not invent timing, nutrition or serving counts.
    steps=[p.strip() for p in re.split(r'\r?\n+',instructions) if p.strip()]
    photo=safe_url(m.get('strMealThumb'))
    if urlparse(photo).hostname not in ('www.themealdb.com','themealdb.com'): photo=''
    return dict(id=key,title=m.get('strMeal') or 'Untitled recipe',image=photo,
        category=m.get('strCategory') or 'Recipe',cuisine=m.get('strArea') or 'Unspecified',
        ingredients=ingredients,steps=steps,source=safe_url(m.get('strSource')),
        video=safe_url(m.get('strYoutube')),provider_url=f'https://www.themealdb.com/meal/{key}',provider='TheMealDB')

def recipes(query,mode='name'):
    endpoint='filter' if mode=='ingredient' else 'search'
    params={'i':query.strip().replace(' ','_')} if mode=='ingredient' else {'s':query}
    try:
        rows=fetch(meal_url(endpoint),params).get('meals') or []
        result=[]
        for m in rows[:18]:
            result.append(normalize(m))
        return result
    except (TypeError,KeyError,ValueError) as exc: raise SourceError('Recipe results could not be read.') from exc

def recipe(recipe_id):
    if not re.fullmatch(r'\d{1,10}',recipe_id): raise SourceError('Invalid recipe identifier.')
    try:
        meals=fetch(meal_url('lookup'),{'i':recipe_id}).get('meals') or []
        if not meals: raise SourceError('This recipe is no longer available from the source.')
        return normalize(meals[0])
    except (TypeError,KeyError,ValueError) as exc: raise SourceError('Recipe details could not be read.') from exc

def guides(query):
    data=fetch('https://en.wikibooks.org/w/api.php',{'action':'query','list':'search','srsearch':query+' prefix:Cookbook:','srlimit':6,'format':'json'})
    try:
        return [dict(title=p['title'].removeprefix('Cookbook:'),snippet=html.unescape(re.sub('<[^>]+>','',p.get('snippet',''))),
                     url=f"https://en.wikibooks.org/?curid={int(p['pageid'])}") for p in data['query']['search'] if p['title'].startswith('Cookbook:')]
    except (KeyError,TypeError,ValueError) as exc: raise SourceError('Cookbook guide results could not be read.') from exc
