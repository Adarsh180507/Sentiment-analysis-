from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import googleapiclient.discovery
import googleapiclient.errors
from urllib.parse import urlparse, parse_qs
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.util import ngrams
from collections import Counter
import nltk
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
import re
import os

app = Flask(__name__)  # Fixed: double underscores
CORS(app)

if not os.path.exists('static'):
    os.makedirs('static')

nltk.download('vader_lexicon', quiet=True)
nltk.download('stopwords', quiet=True)
sia = SentimentIntensityAnalyzer()
stop_words = set(nltk.corpus.stopwords.words('english'))

class EnhancedCommentAnalyzer:
    def __init__(self):  # Fixed: double underscores
        self.comments = []
        self.sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        self.key_phrases = []
        self.insights = []
        self.bigram_counts_negative = Counter()
        self.trigram_counts_negative = Counter()
    
    def clean_url(self, url):
        return re.sub(r'(\?|&)si=.*', '', url)
    
    def extract_video_id(self, url):
        clean_url = self.clean_url(url)
        parsed = urlparse(clean_url)
        
        if "youtube.com" in clean_url:
            query = parse_qs(parsed.query)
            return query.get('v', [parsed.path.split('/')[-1]])[0]
        if "youtu.be" in clean_url:
            return parsed.path.split('/')[-1]
        return parsed.path.split('/')[-1]
    
    def scrape_comments(self, video_url):
        video_id = self.extract_video_id(video_url)
        
        try:
            youtube = googleapiclient.discovery.build(
                "youtube", "v3", 
                developerKey="AIzaSyBndNap9EZA0RY_u7n0t5M28DkJQ9S_QAk"  # Replace with your API key
            )
            
            next_page_token = None
            while True:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=15000,
                    pageToken=next_page_token
                )
                response = request.execute()
                self.comments.extend(response.get('items', []))
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
                    
        except googleapiclient.errors.HttpError as e:
            print(f"API Error: {str(e)}")
            return False
        return True
    
    def get_categorized_comments(self):
        categorized_comments = {
            'positive': [],
            'neutral': [],
            'negative': []
        }
        
        for comment in self.comments:
            text = comment['snippet']['topLevelComment']['snippet']['textDisplay']
            author = comment['snippet']['topLevelComment']['snippet']['authorDisplayName']
            scores = sia.polarity_scores(text)
            
            comment_data = {
                'text': text,
                'author': author,
                'likes': comment['snippet']['topLevelComment']['snippet'].get('likeCount', 0)
            }
            
            if scores['compound'] >= 0.05:
                categorized_comments['positive'].append(comment_data)
            elif scores['compound'] <= -0.05:
                categorized_comments['negative'].append(comment_data)
            else:
                categorized_comments['neutral'].append(comment_data)
        
        return categorized_comments
    
    def analyze_sentiments(self):
        negative_comments_texts = []
        
        for comment in self.comments:
            text = comment['snippet']['topLevelComment']['snippet']['textDisplay']
            
            scores = sia.polarity_scores(text)
            if scores['compound'] >= 0.05:
                self.sentiment_counts['positive'] += 1
            elif scores['compound'] <= -0.05:
                self.sentiment_counts['negative'] += 1
                negative_comments_texts.append(text)
            else:
                self.sentiment_counts['neutral'] += 1
            
            phrases = re.findall(r'\b\w{4,}\b', text.lower())
            self.key_phrases.extend(phrases)
        
        self.bigram_counts_negative = self._extract_ngrams(negative_comments_texts, n=2)
        self.trigram_counts_negative = self._extract_ngrams(negative_comments_texts, n=3)
        self._generate_insights()
        return True
    
    def _extract_ngrams(self, comments, n=2):
        all_phrases = []
        
        def clean_text(text):
            text = text.lower()
            text = re.sub(r'[^a-zA-Z\s]', '', text)
            tokens = [word for word in text.split() if word not in stop_words]
            return tokens  # Fixed: completed the function
        
        for comment in comments:
            tokens = clean_text(comment)
            n_grams = list(ngrams(tokens, n))
            all_phrases.extend([' '.join(gram) for gram in n_grams])
        
        return Counter(all_phrases)
    
    def _generate_insights(self):
        total = sum(self.sentiment_counts.values())
        
        if total > 0:  # Added check to prevent division by zero
            self.insights.append({
                'type': 'distribution',
                'data': {
                    'positive': round(self.sentiment_counts['positive']/total*100, 1),
                    'neutral': round(self.sentiment_counts['neutral']/total*100, 1),
                    'negative': round(self.sentiment_counts['negative']/total*100, 1)
                }
            })
        
        top_phrases = Counter(self.key_phrases).most_common(5)
        self.insights.append({
            'type': 'phrases',
            'data': dict(top_phrases)
        })
        
        if self.sentiment_counts['negative'] > self.sentiment_counts['positive']:
            self.insights.append({
                'type': 'recommendation',
                'data': 'High negative sentiment detected. Consider addressing common concerns in your next video.'
            })
    
    def visualize_data(self):
        plt.figure(figsize=(20, 10))
        
        plt.subplot(2, 2, 1)
        plt.pie(self.sentiment_counts.values(), 
                labels=self.sentiment_counts.keys(),
                autopct='%1.1f%%',
                colors=['#4CAF50', '#FFC107', '#F44336'])
        plt.title('Sentiment Distribution', pad=20, fontsize=14)
        
        if self.key_phrases:
            plt.subplot(2, 2, 2)
            phrase_counts = Counter(self.key_phrases).most_common(5)
            phrase_labels, phrase_values = zip(*phrase_counts)
            plt.bar(phrase_labels, phrase_values, color='orange')
            plt.xticks(rotation=45)
            plt.title('Frequent Phrases', pad=20, fontsize=14)
        
        if self.bigram_counts_negative:
            plt.subplot(2, 2, 3)
            bigram_data = self.bigram_counts_negative.most_common(5)
            if bigram_data:
                bigram_labels, bigram_values = zip(*bigram_data)
                plt.bar(bigram_labels, bigram_values, color='skyblue')
                plt.xticks(rotation=45)
                plt.title('Top Bigrams (Negative Comments)', pad=20, fontsize=14)
        
        if self.trigram_counts_negative:
            plt.subplot(2, 2, 4)
            trigram_data = self.trigram_counts_negative.most_common(5)
            if trigram_data:
                trigram_labels, trigram_values = zip(*trigram_data)
                plt.bar(trigram_labels, trigram_values, color='lightgreen')
                plt.xticks(rotation=45)
                plt.title('Top Trigrams (Negative Comments)', pad=20, fontsize=14)
        
        plt.tight_layout()
        plt.savefig('static/analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Create analyzer instance
        analyzer = EnhancedCommentAnalyzer()
        
        # Scrape and analyze comments
        if not analyzer.scrape_comments(url):
            return jsonify({'error': 'Failed to fetch comments'}), 500
        
        analyzer.analyze_sentiments()
        categorized_comments = analyzer.get_categorized_comments()
        
        # Calculate total likes and unique authors
        total_likes = sum(comment['snippet']['topLevelComment']['snippet'].get('likeCount', 0) 
                         for comment in analyzer.comments)
        unique_authors = len({comment['snippet']['topLevelComment']['snippet']['authorDisplayName'] 
                            for comment in analyzer.comments})

        # Generate visualization
        analyzer.visualize_data()

        response_data = {
            'total_comments': len(analyzer.comments),
            'average_likes': round(total_likes / len(analyzer.comments) if analyzer.comments else 0),
            'unique_authors': unique_authors,
            'insights': analyzer.insights,
            'categorized_comments': categorized_comments,
            'chart': 'analysis.png',
            'keywords': [phrase for phrase, _ in Counter(analyzer.key_phrases).most_common(10)]
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":  # Fixed: double underscores
    app.run(debug=True)
