"""PantryPal: discover, save, plan, shop and cook with Python."""
import csv
import io
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import date,timedelta
from fractions import Fraction
from functools import wraps
from pathlib import Path
from flask import Flask,render_template,request,session,g,redirect,url_for,flash,abort,Response
from werkzeug.security import generate_password_hash,check_password_hash
from db import connect,initialize
import sources

ROOT=Path(__file__).resolve().parent
SLOTS=['Breakfast','Lunch','Dinner']
BATCHES=['0.5','1','2','3']

def clean(value,label,maximum=160,optional=False):
    value=(value or '').strip()
    if (not value and not optional) or len(value)>maximum: raise ValueError(f'{label}: enter {"up to " if optional else "1–"}{maximum} characters.')
    return value

def parse_day(value):
    try: return date.fromisoformat(value)
    except (ValueError,TypeError): raise ValueError('Choose a valid date.') from None

def scale(measure,batches):
    """Scale only simple leading quantities; ambiguous source wording stays explicit."""
    if batches=='1': return measure or 'As listed in recipe'
    m=re.fullmatch(r'(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)(\s+[A-Za-z].*)?',measure.strip())
    if not m or (m[2] and re.search(r'\d|\b(?:plus|or|to)\b',m[2],re.I)): return f'{measure or "To taste"} · use {batches}× recipe amount'
    try:
        amount=sum(Fraction(p) for p in m[1].split())*Fraction(batches)
        whole,rest=divmod(amount.numerator,amount.denominator)
        number=(str(whole)+' ' if whole else '')+str(Fraction(rest,amount.denominator)) if rest else str(whole)
        return number+(m[2] or '')
    except (ValueError,ZeroDivisionError): return f'{measure} · use {batches}× recipe amount'

def create_app(database=None,testing=False):
    app=Flask(__name__)
    data_dir=Path(os.environ.get('DATA_DIR',ROOT/'instance')); data_dir.mkdir(parents=True,exist_ok=True)
    production=os.environ.get('PANTRYPAL_ENV')=='production'
    secret=os.environ.get('SECRET_KEY')
    if production and (not secret or len(secret)<32): raise RuntimeError('Set a random SECRET_KEY of at least 32 characters.')
    if not secret:
        path=data_dir/'.session-secret'
        if not path.exists(): path.write_text(secrets.token_hex(32)); path.chmod(0o600)
        secret=path.read_text().strip()
    app.config.update(SECRET_KEY=secret,DATABASE=str(database or data_dir/'pantry.db'),TESTING=testing,
        SESSION_COOKIE_NAME='pantrypal_session',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=production,PERMANENT_SESSION_LIFETIME=timedelta(days=30),MAX_CONTENT_LENGTH=100000)
    initialize(app.config['DATABASE'])
    def db(): return connect(app.config['DATABASE'])
    def limit(bucket,maximum,seconds=600):
        now=int(time.time())
        with db() as c:
            c.execute('BEGIN IMMEDIATE'); row=c.execute('SELECT * FROM limits WHERE bucket=?',(bucket,)).fetchone()
            if row and now-row['started']<seconds:
                if row['count']>=maximum: abort(429,'Please wait a few minutes before trying again.')
                c.execute('UPDATE limits SET count=count+1 WHERE bucket=?',(bucket,))
            else: c.execute('INSERT OR REPLACE INTO limits VALUES (?,?,1)',(bucket,now))
            c.execute('DELETE FROM limits WHERE started<?',(now-86400,))
    @app.before_request
    def before():
        g.user=None; session.setdefault('csrf',secrets.token_hex(24))
        if session.get('uid'):
            with db() as c: g.user=c.execute("SELECT * FROM users WHERE id=? AND (email IS NOT NULL OR created>=datetime('now','-7 days'))",(session['uid'],)).fetchone()
        if request.method=='POST':
            token=request.form.get('csrf','')
            if not token.isascii() or not secrets.compare_digest(token,session['csrf']): abort(400,'Your form expired. Reload and try again.')
    @app.after_request
    def headers(r):
        r.headers['X-Content-Type-Options']='nosniff'; r.headers['X-Frame-Options']='DENY'
        r.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        r.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' https://www.themealdb.com https://themealdb.com data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if not request.path.startswith('/static/'): r.headers['Cache-Control']='no-store'
        return r
    @app.context_processor
    def context(): return dict(user=g.user,csrf=session['csrf'],today=date.today().isoformat(),slots=SLOTS,batch_options=BATCHES,scale=scale)
    def ensure_user():
        if g.user: return g.user['id']
        limit('guest:'+str(request.remote_addr),20)
        with db() as c:
            c.execute("DELETE FROM users WHERE email IS NULL AND created<datetime('now','-7 days')")
            uid=c.execute("INSERT INTO users(name) VALUES ('Home cook')").lastrowid
            g.user=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        session['uid']=uid; session.permanent=True
        return uid
    def required(fn):
        @wraps(fn)
        def inner(*a,**kw):
            if not g.user: return redirect(url_for('auth',mode='login'))
            return fn(*a,**kw)
        return inner
    def load_recipe(rid):
        if not re.fullmatch(r'\d{1,10}',rid): abort(404)
        with db() as c:
            row=c.execute('SELECT data FROM recipes WHERE id=?',(rid,)).fetchone()
            if row: return json.loads(row['data'])
        limit('data:'+str(request.remote_addr),50)
        r=sources.recipe(rid)
        with db() as c: c.execute('INSERT OR IGNORE INTO recipes VALUES (?,?)',(rid,json.dumps(r)))
        return r
    def week_start():
        value=request.values.get('week')
        try: day=parse_day(value) if value else date.today()
        except ValueError: abort(400,'Choose a valid week.')
        if not date(2000,1,1)<=day<=date(2100,12,1): abort(400,'Choose a week between 2000 and 2100.')
        return day-timedelta(days=day.weekday())
    def plans_for(start):
        if not g.user: return []
        with db() as c:
            rows=c.execute('SELECT p.*,r.data FROM plans p JOIN recipes r ON r.id=p.recipe_id WHERE user_id=? AND day>=? AND day<=? ORDER BY day,slot',(g.user['id'],start.isoformat(),(start+timedelta(days=6)).isoformat())).fetchall()
        return [dict(row,recipe=json.loads(row['data'])) for row in rows]
    @app.get('/health')
    def health(): return {'status':'ok'}
    @app.get('/')
    def home(): return render_template('home.html')
    @app.get('/search')
    def search():
        query=request.args.get('q','').strip()[:100]; mode=request.args.get('mode','name')
        if mode not in ('name','ingredient'): mode='name'
        results=[]; reading=[]; errors=[]
        if query:
            limit('search:'+str(request.remote_addr),30)
            # Separate sources fail independently; one outage never hides the other.
            try: results=sources.recipes(query,mode)
            except sources.SourceError as exc: errors.append('TheMealDB: '+str(exc))
            try: reading=sources.guides(query)
            except sources.SourceError as exc: errors.append('Wikibooks Cookbook: '+str(exc))
        return render_template('search.html',query=query,mode=mode,recipes=results,guides=reading,errors=errors)
    @app.get('/recipe/<rid>')
    def recipe(rid):
        try: r=load_recipe(rid)
        except sources.SourceError as exc: return render_template('error.html',message=str(exc)),503
        batches=request.args.get('batches','1')
        if batches not in BATCHES: batches='1'
        saved=None
        if g.user:
            with db() as c: saved=c.execute('SELECT * FROM favorites WHERE user_id=? AND recipe_id=?',(g.user['id'],rid)).fetchone()
        return render_template('recipe.html',recipe=r,batches=batches,saved=saved)
    @app.get('/cook/<rid>')
    def cook(rid):
        try: r=load_recipe(rid)
        except sources.SourceError as exc: return render_template('error.html',message=str(exc)),503
        return render_template('cook.html',recipe=r)
    @app.post('/save/<rid>')
    def save(rid):
        try: load_recipe(rid)
        except sources.SourceError as exc: flash(str(exc),'error'); return redirect(url_for('search'))
        uid=ensure_user()
        with db() as c: c.execute('INSERT OR IGNORE INTO favorites(user_id,recipe_id) VALUES (?,?)',(uid,rid))
        flash('Saved to your recipe box.','success')
        return redirect(url_for('recipe',rid=rid))
    @app.get('/saved')
    def saved():
        rows=[]
        if g.user:
            with db() as c: rows=c.execute('SELECT r.data FROM favorites f JOIN recipes r ON r.id=f.recipe_id WHERE user_id=? ORDER BY f.rowid DESC',(g.user['id'],)).fetchall()
        return render_template('saved.html',recipes=[json.loads(r['data']) for r in rows])
    @app.post('/notes/<rid>')
    @required
    def notes(rid):
        try: note=clean(request.form.get('notes'),'Notes',5000,True)
        except ValueError as exc: flash(str(exc),'error'); return redirect(url_for('recipe',rid=rid))
        with db() as c:
            if not c.execute('SELECT 1 FROM favorites WHERE user_id=? AND recipe_id=?',(g.user['id'],rid)).fetchone(): abort(404)
            c.execute('UPDATE favorites SET notes=? WHERE user_id=? AND recipe_id=?',(note,g.user['id'],rid))
        flash('Your cooking notes are saved.','success'); return redirect(url_for('recipe',rid=rid))
    @app.get('/planner')
    def planner():
        start=week_start(); plans=plans_for(start)
        return render_template('planner.html',start=start,days=[start+timedelta(days=i) for i in range(7)],plans=plans,previous=(start-timedelta(days=7)).isoformat(),next_week=(start+timedelta(days=7)).isoformat())
    @app.post('/plan/<rid>')
    def plan(rid):
        try:
            load_recipe(rid); day=parse_day(request.form.get('day'))
            if not date(2000,1,1)<=day<=date(2100,12,1): raise ValueError('Choose a date between 2000 and 2100.')
            slot=request.form.get('slot'); batches=request.form.get('batches','1')
            if slot not in SLOTS or batches not in BATCHES: raise ValueError('Choose a meal and recipe quantity.')
            uid=ensure_user()
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                if c.execute('SELECT 1 FROM plans WHERE user_id=? AND day=? AND slot=?',(uid,day.isoformat(),slot)).fetchone(): raise ValueError('That meal slot is already filled. Remove it in the planner before choosing another recipe.')
                c.execute('INSERT INTO plans(user_id,recipe_id,day,slot,batches) VALUES (?,?,?,?,?)',(uid,rid,day.isoformat(),slot,batches))
            flash('Added to your meal plan.','success'); return redirect(url_for('planner',week=day.isoformat()))
        except (ValueError,sources.SourceError) as exc: flash(str(exc),'error'); return redirect(url_for('recipe',rid=rid))
    @app.post('/plan/<int:pid>/remove')
    @required
    def remove_plan(pid):
        with db() as c:
            row=c.execute('SELECT * FROM plans WHERE id=? AND user_id=?',(pid,g.user['id'])).fetchone()
            if not row: abort(404)
            c.execute('DELETE FROM plans WHERE id=?',(pid,))
        flash('Meal removed. Shopping items already generated stay on your list.','success')
        return redirect(url_for('planner',week=row['day']))
    @app.post('/shopping/generate')
    @required
    def generate():
        start=week_start(); plans=plans_for(start); count=0
        with db() as c:
            for p in plans:
                for i,ingredient in enumerate(p['recipe']['ingredients']):
                    cursor=c.execute('INSERT OR IGNORE INTO shopping(user_id,name,measure,origin,source_key) VALUES (?,?,?,?,?)',
                        (g.user['id'],ingredient['name'],scale(ingredient['measure'],p['batches']),f"{p['day']} · {p['slot']} · {p['recipe']['title']}",f"plan:{p['id']}:{p['recipe_id']}:{p['day']}:{p['slot']}:{p['batches']}:{i}"))
                    count+=cursor.rowcount
        flash(f'{count} new ingredients added. Existing meal ingredients were not duplicated.','success'); return redirect(url_for('shopping'))
    @app.get('/shopping')
    def shopping():
        rows=[]
        if g.user:
            with db() as c: rows=c.execute('SELECT * FROM shopping WHERE user_id=? ORDER BY done,id',(g.user['id'],)).fetchall()
        return render_template('shopping.html',items=rows,done=sum(r['done'] for r in rows))
    @app.post('/shopping/add')
    def add_item():
        try:
            name=clean(request.form.get('name'),'Item',100); measure=clean(request.form.get('measure'),'Quantity',80,True); uid=ensure_user()
            with db() as c: c.execute('INSERT INTO shopping(user_id,name,measure,origin) VALUES (?,?,?,?)',(uid,name,measure,'Added by you'))
        except ValueError as exc: flash(str(exc),'error')
        return redirect(url_for('shopping'))
    @app.post('/shopping/<int:item_id>/toggle')
    @required
    def toggle(item_id):
        with db() as c:
            if not c.execute('SELECT 1 FROM shopping WHERE id=? AND user_id=?',(item_id,g.user['id'])).fetchone(): abort(404)
            c.execute('UPDATE shopping SET done=1-done WHERE id=?',(item_id,))
        return redirect(url_for('shopping'))
    @app.get('/shopping.csv')
    @required
    def export():
        with db() as c: rows=c.execute('SELECT * FROM shopping WHERE user_id=? ORDER BY done,id',(g.user['id'],)).fetchall()
        out=io.StringIO(); w=csv.writer(out); w.writerow(['Item','Quantity','For meal','Bought'])
        def safe(v): return "'"+v if v.lstrip().startswith(('=','+','-','@')) else v
        for r in rows: w.writerow([safe(r['name']),safe(r['measure']),safe(r['origin']),'Yes' if r['done'] else 'No'])
        return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=pantrypal-shopping.csv'})
    @app.route('/auth/<mode>',methods=['GET','POST'])
    def auth(mode):
        if mode not in ('register','login'): abort(404)
        if request.method=='POST':
            limit('auth:'+str(request.remote_addr),15)
            try:
                email=clean(request.form.get('email'),'Email',254).lower(); password=request.form.get('password','')
                if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise ValueError('Enter a valid email address.')
                if not 10<=len(password)<=128: raise ValueError('Use a password of 10–128 characters.')
                with db() as c:
                    if mode=='register':
                        name=clean(request.form.get('name'),'Name',60)
                        if g.user and not g.user['email']:
                            uid=g.user['id']; c.execute('UPDATE users SET name=?,email=?,password=? WHERE id=?',(name,email,generate_password_hash(password),uid))
                        else: uid=c.execute('INSERT INTO users(name,email,password) VALUES (?,?,?)',(name,email,generate_password_hash(password))).lastrowid
                    else:
                        u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                        if not u or not check_password_hash(u['password'],password): raise ValueError('Email or password is incorrect.')
                        uid=u['id']
                session.clear(); session['uid']=uid; session.permanent=True
                return redirect(url_for('saved'))
            except sqlite3.IntegrityError: flash('That email is already registered. Please sign in.','error')
            except ValueError as exc: flash(str(exc),'error')
        return render_template('auth.html',mode=mode)
    @app.post('/logout')
    def logout(): session.clear(); return redirect(url_for('home'))
    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error(exc): return render_template('error.html',message=exc.description),exc.code
    return app

if __name__=='__main__': create_app().run(host='127.0.0.1',port=5005,debug=False)
