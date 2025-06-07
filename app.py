from flask import Flask, render_template, request, url_for, redirect, flash, session
from news_utils import fetch_articles, get_full_article_text, translate_text
import feedparser
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret_key_here'

app.jinja_env.globals.update(zip=zip)

app.config['DATABASE_URL'] = 'url_here'

def get_db_connection():
    """Connect to the PostgreSQL database."""
    conn = None
    try:
        conn = psycopg2.connect(app.config['DATABASE_URL'])
        conn.autocommit = False 
    except psycopg2.Error as e:
        print(f"Veritabanına bağlanırken hata oluştu: {e}")
    return conn

def fetch_local_rss():
    rss_url = "https://www.cnnturk.com/feed/rss/turkiye/news"
    feed = feedparser.parse(rss_url)
    news_list = []
    for entry in feed.entries:
        image = ""
        if hasattr(entry, 'media_content') and entry.media_content:
            image = entry.media_content[0].get('url', '')
        elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            image = entry.media_thumbnail[0].get('url', '')
        elif hasattr(entry, 'enclosures') and entry.enclosures:
            image = entry.enclosures[0].get('href', '')
        elif hasattr(entry, 'links') and entry.links:
            for link in entry.links:
                if link.get('rel') == 'enclosure' and link.get('type', '').startswith('image'):
                    image = link.get('href', '')
                    break
        date = getattr(entry, "published", "") or getattr(entry, "updated", "")
        description = getattr(entry, "summary", "") or getattr(entry, "description", "")
        preview = description
        if preview:
            words = preview.split()
            if len(words) > 30:
                preview = " ".join(words[:30]) + "..."
        news_list.append({
            "title": getattr(entry, "title", "Başlıksız"),
            "url": getattr(entry, "link", "#"),
            "date": date,
            "description": description, 
            "preview": preview,        
            "image": image
        })
    return news_list

def fetch_trt_rss():
    rss_url = "https://www.trthaber.com/xml_mobile.php?kat=turkiye"
    feed = feedparser.parse(rss_url)
    news_list = []
    for entry in feed.entries:
        image = ""
        date = getattr(entry, "published", "") or getattr(entry, "updated", "")
        description = getattr(entry, "summary", "") or getattr(entry, "description", "")
        news_list.append({
            "title": getattr(entry, "title", "Başlıksız"),
            "url": getattr(entry, "link", "#"),
            "date": date,
            "description": description,
            "image": image
        })
    return news_list

@app.route("/")
def home():
    return redirect(url_for("main"))

@app.route("/main")
def main():
    page = int(request.args.get("page", 1))
    per_page = 12
    all_news = fetch_local_rss()
    total_results = len(all_news)
    start = (page - 1) * per_page
    end = start + per_page
    trt_news = all_news[start:end]
    total_pages = (total_results + per_page - 1) // per_page
    return render_template(
        "main.html",
        trt_news=trt_news,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page
    )

@app.route("/international")
def international():
    page = int(request.args.get("page", 1))
    per_page = 12
    params = {
        'apiKey': 'api_key_here',
        'sortBy': 'publishedAt',
        'pageSize': per_page,
        'page': page,
        'q': 'news'
    }
    articles_data = fetch_articles(params)
    articles = []
    total_results = 0
    if isinstance(articles_data, dict):
        if articles_data.get("status") == "error":
            error_message = articles_data.get("message", "NewsAPI error")
            return render_template("international.html", international_news=[], error=error_message, page=page, total_pages=1, per_page=per_page)
        articles = articles_data.get("articles", [])
        total_results = min(articles_data.get("totalResults", 0), 100)
    elif isinstance(articles_data, list):
        articles = articles_data
        total_results = len(articles)
    international_news = []
    for idx, article in enumerate(articles):
        url = article.get('url')
        title = article.get('title', 'No Title')
        source_name = article.get('source', {}).get('name', 'Unknown')
        published_at = article.get('publishedAt', '')[:10]
        description = article.get('description', '')
        image = article.get('urlToImage', '')
        translated = translate_text(description) if description else ""
        international_news.append({
            "title": title,
            "source": source_name,
            "date": published_at,
            "url": url,
            "description": description,
            "image": image,
            "translated": translated,
            "id": idx + (page-1)*per_page
        })
    total_pages = (total_results + per_page - 1) // per_page if total_results else page
    return render_template(
        "international.html",
        international_news=international_news,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page
    )

@app.route("/foreign_turkey")
def foreign_turkey():
    page = int(request.args.get("page", 1))
    per_page = 12
    params = {
        'apiKey': 'api_key_here',
        'sortBy': 'publishedAt',
        'pageSize': per_page,
        'page': page,
        'q': 'Turkey OR Türkiye'
    }
    articles_data = fetch_articles(params)
    if isinstance(articles_data, dict):
        articles = articles_data.get("articles", [])
        total_results = min(articles_data.get("totalResults", 0), 100)
    else:
        articles = articles_data or []
        total_results = len(articles)
    foreign_news = []
    for idx, article in enumerate(articles):
        url = article.get('url')
        title = article.get('title', 'No Title')
        source_name = article.get('source', {}).get('name', 'Unknown')
        published_at = article.get('publishedAt', '')[:10]
        description = article.get('description', '')
        image = article.get('urlToImage', '')
        foreign_news.append({
            "title": title,
            "source": source_name,
            "date": published_at,
            "url": url,
            "description": description,
            "image": image,
            "id": idx + (page-1)*per_page
        })
    total_pages = (total_results + per_page - 1) // per_page if total_results else page
    return render_template(
        "foreign_turkey.html",
        foreign_news=foreign_news,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page
    )

@app.route("/foreign_turkey/article/<int:article_id>")
def foreign_turkey_article(article_id):
    params = {
        'apiKey': 'api_key_here',
        'sortBy': 'publishedAt',
        'pageSize': 10,
        'q': 'Turkey OR Türkiye'
    }
    articles_data = fetch_articles(params)
    if isinstance(articles_data, dict):
        articles = articles_data.get("articles", [])
    else:
        articles = articles_data or []
    # Sidebar news for "Bunlara da göz atın"
    sidebar_news = []
    for idx, article in enumerate(articles):
        if idx == article_id:
            continue
        sidebar_news.append({
            "title": article.get("title", "No Title"),
            "date": article.get("publishedAt", "")[:10],
            "id": idx
        })
        if len(sidebar_news) >= 5:
            break

    related_topics = []
    if 0 <= article_id < len(articles):
        article = articles[article_id]
        url = article.get('url')
        title = article.get('title', 'No Title')
        source_name = article.get('source', {}).get('name', 'Unknown')
        published_at = article.get('publishedAt', '')[:10]
        description = article.get('description', '')
        content = get_full_article_text(url) if url else ""
        translated = translate_text(content) if content else ""
        keywords = []
        if title:
            for word in title.split():
                w = word.strip(",.?!:;").lower()
                if len(w) > 3 and w not in [
                    "with", "from", "that", "this", "have", "been", "will", "your", "about", "over", "after", "before",
                    "their", "they", "said", "says", "for", "the", "and", "but", "not", "are", "has", "was", "who",
                    "her", "his", "she", "him", "you", "our", "new"
                ]:
                    keywords.append(w)
        search_query = " ".join(keywords[:2]) if keywords else ""
        if search_query:
            params_related = {
                'apiKey': 'api_key_here',
                'sortBy': 'relevancy',
                'pageSize': 5,
                'q': search_query
            }
            related_data = fetch_articles(params_related)
            if isinstance(related_data, dict):
                related_articles = related_data.get("articles", [])
            else:
                related_articles = related_data or []
            for rel in related_articles:
                rel_title = rel.get("title", "")
                rel_url = rel.get("url", "#")
                if rel_title != title:
                    related_topics.append({"title": rel_title, "url": rel_url})

        from flask import session, flash, redirect, url_for, request
        if request.method == "POST" and session.get("email"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (session["email"],))
            user_row = cur.fetchone()
            if user_row:
                user_id = user_row[0]
                cur.execute(
                    "INSERT INTO news (user_id, title, content, saved_at) VALUES (%s, %s, %s, %s)",
                    (user_id, title, content, datetime.now())
                )
                conn.commit()
                flash("Haber arşivinize kaydedildi.", "success")
            cur.close()
            conn.close()
            return redirect(url_for('foreign_turkey_article', article_id=article_id))

        return render_template(
            "foreign_turkey_article.html",
            article={
                "title": title,
                "source": source_name,
                "date": published_at,
                "url": url,
                "translated": translated
            },
            back=url_for('foreign_turkey'),
            sidebar_news=sidebar_news,
            related_topics=related_topics
        )
    return "Article not found", 404

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password, first_name FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user[1], password):
            session['email'] = email  # Store user info in session
            session['first_name'] = user[2]
            flash('Giriş başarılı!', 'success')
            return redirect(url_for('main'))
        else:
            flash('Giriş başarısız. Lütfen e-posta ve şifrenizi kontrol edin.', 'danger')
        cur.close()
        conn.close()
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('email', None)
    session.pop('first_name', None)
    return redirect(url_for('main'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (email, first_name, last_name, password) VALUES (%s, %s, %s, %s)",
                (email, first_name, last_name, hashed_password),
            )
            conn.commit()
            flash('Kayıt başarılı! Lütfen giriş yapın.', 'success')
            return redirect(url_for('login'))
        except psycopg2.Error as e:
            conn.rollback()
            flash(f'Kayıt başarısız. Hata: {e}', 'danger')
        finally:
            cur.close()
            conn.close()

    return render_template("register.html")

@app.route("/account")
def account():
    if not session.get('email'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email, first_name, last_name FROM users WHERE email = %s", (session['email'],))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        return render_template('account.html', user=user)
    else:
        flash('Kullanıcı bilgileri bulunamadı.', 'danger')
        return redirect(url_for('main'))

@app.route("/article/<int:article_id>", methods=["GET", "POST"])
def view_article(article_id):
    from_page = request.args.get("from", "main")
    if from_page == "main":
        articles = fetch_local_rss()
        sidebar_news = fetch_local_rss()[:5]
    elif from_page == "international":
        params = {
            'apiKey': 'api_key_here',
            'language': 'en',
            'sortBy': 'popularity',
            'pageSize': 10,
            'q': 'Turkey OR Türkiye'
        }
        articles_data = fetch_articles(params)
        if isinstance(articles_data, dict):
            articles = articles_data.get("articles", [])
        else:
            articles = articles_data or []
        sidebar_news = []
        for idx, article in enumerate(articles):
            if idx == article_id:
                continue
            sidebar_news.append({
                "title": article.get("title", "No Title"),
                "date": article.get("publishedAt", "")[:10],
                "id": idx
            })
            if len(sidebar_news) >= 5:
                break
    else:
        articles = []
        sidebar_news = []

    related_topics = []
    if 0 <= article_id < len(articles):
        article = articles[article_id]
        title = article.get('title', '')
        keywords = []
        if title:
            for word in title.split():
                w = word.strip(",.?!:;").lower()
                if len(w) > 3 and w not in ["with", "from", "that", "this", "have", "been", "will", "your", "about", "over", "after", "before", "their", "they", "said", "says", "for", "the", "and", "but", "not", "are", "has", "was", "who", "her", "his", "she", "him", "you", "our", "new"]:
                    keywords.append(w)
        search_query = " ".join(keywords[:2]) if keywords else ""
        if search_query:
            params_related = {
                'apiKey': 'api_key_here',
                'language': 'en',
                'sortBy': 'relevancy',
                'pageSize': 5,
                'q': search_query
            }
            related_data = fetch_articles(params_related)
            if isinstance(related_data, dict):
                related_articles = related_data.get("articles", [])
            else:
                related_articles = related_data or []
            for rel in related_articles:
                rel_title = rel.get("title", "")
                rel_url = rel.get("url", "#")
                if rel_title != title:
                    related_topics.append({"title": rel_title, "url": rel_url})
   
    if 0 <= article_id < len(articles):
        article = articles[article_id]
        url = article.get('url')
        title = article.get('title', 'No Title')
        source_name = article.get('source', {}).get('name', 'Unknown') if isinstance(article, dict) else article.get('source', 'CNN Turk')
        published_at = article.get('publishedAt', '')[:10] if isinstance(article, dict) else article.get('date', '')
        if from_page == "main" or source_name == "CNN Turk":
            content = get_full_article_text(url) if url else ""
            translated = content
        else:
            content = get_full_article_text(url) if url else ""
            translated = translate_text(content) if content else ""

        if request.method == "POST" and session.get("email"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (session["email"],))
            user_row = cur.fetchone()
            if user_row:
                user_id = user_row[0]
                cur.execute(
                    "INSERT INTO news (user_id, title, content, saved_at) VALUES (%s, %s, %s, %s)",
                    (user_id, title, content, datetime.now())
                )
                conn.commit()
                flash("Haber arşivinize kaydedildi.", "success")
            cur.close()
            conn.close()
            return redirect(url_for('view_article', article_id=article_id, from_=from_page))

        return render_template(
            "article.html",
            article={
                "title": title,
                "source": source_name,
                "date": published_at,
                "url": url,
                "translated": translated
            },
            back=url_for(from_page),
            sidebar_news=sidebar_news,
            from_page=from_page,
            related_topics=related_topics
        )
    return "Article not found", 404

@app.route("/arsiv")
def arsiv():
    if not session.get("email"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (session["email"],))
    user_row = cur.fetchone()
    news_list = []
    if user_row:
        user_id = user_row[0]
        cur.execute("SELECT title, content, saved_at FROM news WHERE user_id = %s ORDER BY saved_at DESC", (user_id,))
        news_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("arsiv.html", news_list=news_list)

@app.route("/arsiv/view/<int:news_id>")
def arsiv_view(news_id):
    if not session.get("email"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (session["email"],))
    user_row = cur.fetchone()
    news = None
    if user_row:
        user_id = user_row[0]
        cur.execute("SELECT title, content, saved_at FROM news WHERE user_id = %s ORDER BY saved_at DESC", (user_id,))
        news_list = cur.fetchall()
        if 0 <= news_id < len(news_list):
            news = news_list[news_id]
    cur.close()
    conn.close()
    if news:
        return render_template("arsiv_view.html", news=news)
    return "Arşiv haberi bulunamadı.", 404

def fetch_local_category_rss(category):
    rss_map = {
        "Ekonomi": "https://www.cnnturk.com/feed/rss/ekonomi/news",
        "Spor": "https://www.cnnturk.com/feed/rss/spor/news",
        "Sağlık": "https://www.cnnturk.com/feed/rss/saglik/news",
        "Teknoloji": "https://www.cnnturk.com/feed/rss/teknoloji/news",
        "Siyaset": "https://www.cnnturk.com/feed/rss/politika/news",
    }
    rss_url = rss_map.get(category)
    if not rss_url:
        return []
    feed = feedparser.parse(rss_url)
    news_list = []
    for entry in feed.entries:
        image = ""
        if hasattr(entry, 'media_content') and entry.media_content:
            image = entry.media_content[0].get('url', '')
        elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            image = entry.media_thumbnail[0].get('url', '')
        elif hasattr(entry, 'enclosures') and entry.enclosures:
            image = entry.enclosures[0].get('href', '')
        elif hasattr(entry, 'links') and entry.links:
            for link in entry.links:
                if link.get('rel') == 'enclosure' and link.get('type', '').startswith('image'):
                    image = link.get('href', '')
                    break
        date = getattr(entry, "published", "") or getattr(entry, "updated", "")
        url = getattr(entry, "link", "#")
        title = getattr(entry, "title", "Başlıksız")
        full_content = get_full_article_text(url) if url and url != "#" else ""
        if not full_content:
            full_content = getattr(entry, "summary", "") or getattr(entry, "description", "")
        preview = full_content
        if preview:
            words = preview.split()
            if len(words) > 30:
                preview = " ".join(words[:30]) + "..."
        news_list.append({
            "title": title,
            "url": url,
            "date": date,
            "description": preview,         
            "image": image,
            "full_content": full_content  
        })
    return news_list

@app.route("/ekonomi")
def ekonomi():
    page = int(request.args.get("page", 1))
    per_page = 12
    all_news = fetch_local_category_rss("Ekonomi")
    total_results = len(all_news)
    start = (page - 1) * per_page
    end = start + per_page
    news_list = all_news[start:end]
    total_pages = (total_results + per_page - 1) // per_page
    return render_template(
        "category.html",
        news_list=news_list,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page,
        category="Ekonomi"
    )

@app.route("/spor")
def spor():
    page = int(request.args.get("page", 1))
    per_page = 12
    all_news = fetch_local_category_rss("Spor")
    total_results = len(all_news)
    start = (page - 1) * per_page
    end = start + per_page
    news_list = all_news[start:end]
    total_pages = (total_results + per_page - 1) // per_page
    return render_template(
        "category.html",
        news_list=news_list,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page,
        category="Spor"
    )

@app.route("/saglik")
def saglik():
    page = int(request.args.get("page", 1))
    per_page = 12
    all_news = fetch_local_category_rss("Sağlık")
    total_results = len(all_news)
    start = (page - 1) * per_page
    end = start + per_page
    news_list = all_news[start:end]
    total_pages = (total_results + per_page - 1) // per_page
    return render_template(
        "category.html",
        news_list=news_list,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page,
        category="Sağlık"
    )

@app.route("/teknoloji")
def teknoloji():
    page = int(request.args.get("page", 1))
    per_page = 12
    all_news = fetch_local_category_rss("Teknoloji")
    total_results = len(all_news)
    start = (page - 1) * per_page
    end = start + per_page
    news_list = all_news[start:end]
    total_pages = (total_results + per_page - 1) // per_page
    return render_template(
        "category.html",
        news_list=news_list,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page,
        category="Teknoloji"
    )

@app.route("/siyaset")
def siyaset():
    page = int(request.args.get("page", 1))
    per_page = 12
    all_news = fetch_local_category_rss("Siyaset")
    total_results = len(all_news)
    start = (page - 1) * per_page
    end = start + per_page
    news_list = all_news[start:end]
    total_pages = (total_results + per_page - 1) // per_page
    return render_template(
        "category.html",
        news_list=news_list,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        per_page=per_page,
        category="Siyaset"
    )

@app.route("/category/<category>/<int:article_id>", methods=["GET", "POST"])
def view_category_article(category, article_id):
    all_news = fetch_local_category_rss(category)
    if 0 <= article_id < len(all_news):
        article = all_news[article_id]
        title = article.get("title", "Başlıksız")
        source_name = "CNN Türk"
        published_at = article.get("date", "")
        url = article.get("url", "#")
        description = article.get("full_content", "")
        image = article.get("image", "")

        sidebar_news = []
        for idx, news in enumerate(all_news):
            if idx == article_id:
                continue
            sidebar_news.append({
                "title": news.get("title", "Başlıksız"),
                "date": news.get("date", ""),
                "id": idx
            })
            if len(sidebar_news) >= 5:
                break

        related_topics = []
        keywords = []
        if title:
            for word in title.split():
                w = word.strip(",.?!:;").lower()
                if len(w) > 3 and w not in [
                    "with", "from", "that", "this", "have", "been", "will", "your", "about", "over", "after", "before",
                    "their", "they", "said", "says", "for", "the", "and", "but", "not", "are", "has", "was", "who",
                    "her", "his", "she", "him", "you", "our", "new"
                ]:
                    keywords.append(w)
        search_query = " ".join(keywords[:2]) if keywords else ""
        if search_query:
            for idx, news in enumerate(all_news):
                if idx == article_id:
                    continue
                news_title = news.get("title", "")
                if all(k.lower() in news_title.lower() for k in keywords[:2]):
                    related_topics.append({
                        "title": news_title,
                        "url": url_for('view_category_article', category=category, article_id=idx)
                    })
                if len(related_topics) >= 5:
                    break

        if request.method == "POST" and session.get("email"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (session["email"],))
            user_row = cur.fetchone()
            if user_row:
                user_id = user_row[0]
                cur.execute(
                    "INSERT INTO news (user_id, title, content, saved_at) VALUES (%s, %s, %s, %s)",
                    (user_id, title, description, datetime.now())
                )
                conn.commit()
                flash("Haber arşivinize kaydedildi.", "success")
            cur.close()
            conn.close()
            return redirect(url_for('view_category_article', category=category, article_id=article_id))

        endpoint_map = {
            "Ekonomi": "ekonomi",
            "Spor": "spor",
            "Sağlık": "saglik",
            "Teknoloji": "teknoloji",
            "Siyaset": "siyaset"
        }
        back_endpoint = endpoint_map.get(category, "main")
        return render_template(
            "category_article.html",
            article={
                "title": title,
                "source": source_name,
                "date": published_at,
                "url": url,
                "description": description,
                "image": image
            },
            back=url_for(back_endpoint),
            sidebar_news=sidebar_news,
            related_topics=related_topics,
            category=category
        )
    return "Article not found", 404

if __name__ == "__main__":
    app.run(debug=True)
