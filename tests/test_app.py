import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import create_app, scale
from db import connect
from sources import SourceError, safe_url

RECIPE=dict(id='52771',title='Test pasta',image='',category='Pasta',cuisine='Italian',ingredients=[{'name':'Pasta','measure':'1 cup'},{'name':'Basil','measure':'to taste'}],steps=['Boil water.','Cook pasta.'],source='',video='',provider_url='https://www.themealdb.com/meal/52771',provider='TheMealDB')
class KitchenTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=Path(self.temp.name)/'test.db'
        self.app=create_app(self.path,testing=True); self.client=self.app.test_client()
        self.mock=patch('sources.recipe',return_value=RECIPE); self.mock.start()
    def tearDown(self): self.mock.stop(); self.temp.cleanup()
    def post(self,url,data=None,client=None):
        client=client or self.client; client.get('/')
        with client.session_transaction() as s: token=s['csrf']
        return client.post(url,data=dict(data or {},csrf=token),follow_redirects=True)
    def rows(self,table):
        with connect(self.path) as c: return c.execute('SELECT * FROM '+table).fetchall()
    def plan(self,day='2026-10-05',slot='Dinner'):
        return self.post('/plan/52771',dict(day=day,slot=slot,batches='2'))
    def test_public_pages(self):
        for path in ['/','/search','/planner','/saved','/shopping','/recipe/52771','/cook/52771']:
            self.assertEqual(self.client.get(path).status_code,200,path)
    def test_csrf(self): self.assertEqual(self.client.post('/save/52771').status_code,400)
    def test_save_idempotent(self):
        self.post('/save/52771'); self.post('/save/52771'); self.assertEqual(len(self.rows('favorites')),1)
    def test_recipe_cached(self):
        self.client.get('/recipe/52771')
        with patch('sources.recipe',side_effect=SourceError('Offline')):
            self.assertEqual(self.client.get('/recipe/52771').status_code,200)
    def test_sources_fail_independently(self):
        with patch('sources.recipes',side_effect=SourceError('Offline')),patch('sources.guides',return_value=[dict(title='Pasta guide',snippet='Useful',url='https://en.wikibooks.org/')]):
            r=self.client.get('/search?q=pasta'); self.assertIn(b'Pasta guide',r.data); self.assertIn(b'Offline',r.data)
    def test_plan_conflict(self):
        self.plan(); r=self.plan(); self.assertEqual(len(self.rows('plans')),1); self.assertIn(b'already filled',r.data)
    def test_plan_validation(self):
        self.plan('bad'); self.plan(slot='invalid'); self.assertEqual(len(self.rows('plans')),0)
    def test_shopping_dedup_and_scale(self):
        self.plan(); self.post('/shopping/generate',{'week':'2026-10-05'}); self.post('/shopping/generate',{'week':'2026-10-05'})
        rows=self.rows('shopping'); self.assertEqual(len(rows),2); self.assertEqual(rows[0]['measure'],'2 cup')
    def test_reused_plan_id(self):
        self.plan(); self.post('/shopping/generate',{'week':'2026-10-05'})
        pid=self.rows('plans')[0]['id']; self.post(f'/plan/{pid}/remove'); self.plan('2026-10-06')
        self.post('/shopping/generate',{'week':'2026-10-05'}); self.assertEqual(len(self.rows('shopping')),4)
    def test_private_items(self):
        self.post('/shopping/add',{'name':'Private apple'}); item=self.rows('shopping')[0]['id']
        other=self.app.test_client(); self.post('/shopping/add',{'name':'Other apple'},other)
        self.assertNotIn(b'Private apple',other.get('/shopping').data)
        self.assertEqual(self.post(f'/shopping/{item}/toggle',client=other).status_code,404)
    def test_toggle(self):
        self.post('/shopping/add',{'name':'Apple'}); item=self.rows('shopping')[0]['id']
        self.post(f'/shopping/{item}/toggle'); self.assertEqual(self.rows('shopping')[0]['done'],1)
    def test_csv_formula(self):
        self.post('/shopping/add',{'name':'=1+1'}); self.assertIn(b"'=1+1",self.client.get('/shopping.csv').data)
    def test_guest_registration_retains_library(self):
        self.post('/save/52771'); uid=self.rows('users')[0]['id']
        self.post('/auth/register',dict(name='Test cook',email='cook@example.test',password='test-only-password'))
        self.assertEqual(self.rows('users')[0]['id'],uid); self.assertEqual(len(self.rows('favorites')),1)
        self.post('/logout'); self.assertNotIn(b'Test pasta',self.client.get('/saved').data)
        self.post('/auth/login',dict(email='cook@example.test',password='test-only-password'))
        self.assertIn(b'Test pasta',self.client.get('/saved').data)
    def test_notes_escaped(self):
        self.post('/save/52771'); r=self.post('/notes/52771',{'notes':'<script>alert(1)</script>'})
        self.assertNotIn(b'<script>alert(1)</script>',r.data); self.assertIn(b'&lt;script&gt;',r.data)
    def test_scale_ambiguous(self):
        self.assertEqual(scale('1 1/2 cups','2'),'3 cups')
        self.assertIn('use 2',scale('1 cup plus 1 tsp','2'))
        self.assertIn('use 2',scale('1-2 cups','2'))
    def test_source_url(self): self.assertEqual(safe_url('javascript:alert(1)'), '')
    def test_invalid_recipe_and_week(self):
        self.assertEqual(self.client.get('/recipe/nope').status_code,404)
        self.assertEqual(self.client.get('/planner?week=bad').status_code,400)
if __name__=='__main__': unittest.main()
