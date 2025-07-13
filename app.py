from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import os
from datetime import date, datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
DB_NAME = os.environ.get('DATABASE_URL', 'collection.db')

def init_db():
    if not os.path.exists(DB_NAME):
        with open('schema.sql', 'r') as f:
            schema = f.read()
        conn = sqlite3.connect(DB_NAME)
        conn.executescript(schema)
        conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db()
    cur = conn.cursor()
    today = request.args.get('date') or date.today().isoformat()
    message = ''
    message_type = 'warning'
    
    if request.method == 'POST':
        if 'add_person' in request.form:
            name = request.form.get('person_name', '').strip()
            if name:
                try:
                    cur.execute('INSERT INTO people (name) VALUES (?)', (name,))
                    conn.commit()
                    message = f'Successfully added {name} to the collection list.'
                    message_type = 'success'
                except sqlite3.IntegrityError:
                    message = f'Person "{name}" already exists in the list.'
                    message_type = 'warning'
                except Exception as e:
                    message = f'Error adding person: {str(e)}'
                    message_type = 'warning'
        
        elif 'save_collections' in request.form:
            try:
                saved_count = 0
                for key in request.form:
                    if key.startswith('collected_'):
                        person_id = key.split('_')[1]
                        collected = request.form.get(f'collected_{person_id}') == 'on'
                        amount = request.form.get(f'amount_{person_id}') or 0
                        
                        cur.execute('''
                            INSERT INTO collections (person_id, date, collected, amount) 
                            VALUES (?, ?, ?, ?) 
                            ON CONFLICT(person_id, date) 
                            DO UPDATE SET collected=excluded.collected, amount=excluded.amount
                        ''', (person_id, today, collected, amount))
                        saved_count += 1
                
                conn.commit()
                message = f'Successfully saved {saved_count} collection records for {today}.'
                message_type = 'success'
            except Exception as e:
                message = f'Error saving collections: {str(e)}'
                message_type = 'warning'
    
    cur.execute('SELECT * FROM people ORDER BY name')
    people = cur.fetchall()
    
    cur.execute('SELECT * FROM collections WHERE date = ?', (today,))
    collections = {row['person_id']: row for row in cur.fetchall()}
    
    stats = get_statistics(cur, today)
    
    conn.close()
    return render_template('index.html', 
                         people=people, 
                         collections=collections, 
                         today=today, 
                         message=message,
                         message_type=message_type,
                         stats=stats)

def get_statistics(cur, selected_date):
    cur.execute('''
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN collected = 1 THEN 1 ELSE 0 END) as collected_count,
               SUM(CASE WHEN collected = 1 THEN amount ELSE 0 END) as total_amount
        FROM collections 
        WHERE date = ?
    ''', (selected_date,))
    daily_stats = cur.fetchone()
    
    week_start = (datetime.strptime(selected_date, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d')
    cur.execute('''
        SELECT SUM(amount) as weekly_total
        FROM collections 
        WHERE date BETWEEN ? AND ? AND collected = 1
    ''', (week_start, selected_date))
    weekly_stats = cur.fetchone()
    
    month_start = selected_date[:7] + '-01'
    cur.execute('''
        SELECT SUM(amount) as monthly_total
        FROM collections 
        WHERE date BETWEEN ? AND ? AND collected = 1
    ''', (month_start, selected_date))
    monthly_stats = cur.fetchone()
    
    return {
        'daily': {
            'total': daily_stats['total'] or 0,
            'collected': daily_stats['collected_count'] or 0,
            'amount': daily_stats['total_amount'] or 0
        },
        'weekly': {
            'amount': weekly_stats['weekly_total'] or 0
        },
        'monthly': {
            'amount': monthly_stats['monthly_total'] or 0
        }
    }

@app.route('/delete/<int:person_id>')
def delete_person(person_id):
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT name FROM people WHERE id = ?', (person_id,))
        person = cur.fetchone()
        
        if person:
            cur.execute('DELETE FROM collections WHERE person_id = ?', (person_id,))
            cur.execute('DELETE FROM people WHERE id = ?', (person_id,))
            conn.commit()
            
            flash(f'Successfully removed {person["name"]} from the collection list.', 'success')
        else:
            flash('Person not found.', 'warning')
            
    except Exception as e:
        flash(f'Error deleting person: {str(e)}', 'warning')
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/stats/<date>')
def get_stats_api(date):
    conn = get_db()
    cur = conn.cursor()
    stats = get_statistics(cur, date)
    conn.close()
    return jsonify(stats)

@app.route('/api/collections/<date>')
def get_collections_api(date):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT p.name, c.collected, c.amount 
        FROM collections c 
        JOIN people p ON c.person_id = p.id 
        WHERE c.date = ?
        ORDER BY p.name
    ''', (date,))
    
    collections = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(collections)

@app.route('/history')
def history():
    conn = get_db()
    cur = conn.cursor()
    
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    
    cur.execute('''
        SELECT c.date, p.name, c.collected, c.amount
        FROM collections c
        JOIN people p ON c.person_id = p.id
        WHERE c.date >= ?
        ORDER BY c.date DESC, p.name
    ''', (thirty_days_ago,))
    
    history_data = cur.fetchall()
    
    history_by_date = {}
    for row in history_data:
        date_str = row['date']
        if date_str not in history_by_date:
            history_by_date[date_str] = []
        history_by_date[date_str].append(dict(row))
    
    conn.close()
    return render_template('history.html', history=history_by_date)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 