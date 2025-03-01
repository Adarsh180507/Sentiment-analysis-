const form = document.getElementById('analysisForm');
const loading = document.querySelector('.loading');
const results = document.getElementById('results');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    loading.style.display = 'block';
    results.style.display = 'none';
    
    try {
        const url = form.querySelector('input[name="url"]').value;
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to analyze comments');
        }
        
        const data = await response.json();
        window.commentData = data.categorized_comments;
        updateUI(data);
        
    } catch (error) {
        alert(error.message || 'An error occurred while analyzing comments');
    } finally {
        loading.style.display = 'none';
    }
});

function updateUI(data) {
    // Update comment count
    document.getElementById('commentCount').textContent = data.total_comments;
    
    // Update sentiment distribution
    const distribution = data.insights.find(i => i.type === 'distribution').data;
    
    // Update sentiment cards
    const sentimentTypes = ['positive', 'neutral', 'negative'];
    sentimentTypes.forEach(type => {
        const progressBar = document.getElementById(`${type}Score`);
        if (progressBar) {
            progressBar.style.width = `${distribution[type]}%`;
            progressBar.textContent = `${type.charAt(0).toUpperCase() + type.slice(1)}: ${distribution[type]}%`;
        }
    });
    
    // Update key metrics
    const metrics = {
        totalComments: data.total_comments,
        avgLikes: Math.round(data.average_likes) || 0,
        uniqueAuthors: data.unique_authors || data.total_authors || 0,
        engagementRate: ((data.total_likes / data.total_comments) * 100).toFixed(1) + '%'
    };

    Object.entries(metrics).forEach(([key, value]) => {
        const element = document.getElementById(key);
        if (element) element.textContent = value;
    });

    // Update keywords/phrases
    const phrasesData = data.insights.find(i => i.type === 'phrases')?.data || {};
    const keywordsList = document.getElementById('keywordsList');
    if (keywordsList) {
        const topPhrases = Object.entries(phrasesData)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        keywordsList.innerHTML = topPhrases.map(([phrase, count]) => 
            `<span class="keyword-tag">${phrase} (${count})</span>`
        ).join('');
    }

    // Update chart
    const chartImg = document.getElementById('chart');
    if (chartImg && data.chart) {
        chartImg.src = `${data.chart}?t=${Date.now()}`;
    }

    // Update insights cards
    updateInsights(data);

    // Show results and display comments
    results.style.display = 'block';
    displayComments(data.categorized_comments, 'positive');

    // Apply animations
    document.querySelectorAll('#results > *').forEach((el, index) => {
        el.classList.add('animate__animated', 'animate__fadeIn');
        el.style.animationDelay = `${0.1 * index}s`;
    });
}

function displayComments(comments, category) {
    const container = document.getElementById('comments-container');
    container.innerHTML = '';
    
    if (!comments || !comments[category] || comments[category].length === 0) {
        container.innerHTML = '<div class="alert alert-info">No comments in this category</div>';
        return;
    }
    
    comments[category].forEach((comment, index) => {
        const commentEl = document.createElement('div');
        commentEl.className = `comment-card ${category}-comment animate__animated animate__fadeIn`;
        commentEl.style.animationDelay = `${0.05 * index}s`;
        commentEl.innerHTML = `
            <div class="comment-header">
                <div class="comment-author">
                    <i class="fas fa-user-circle"></i> ${comment.author}
                </div>
                <div class="comment-likes">
                    <i class="fas fa-thumbs-up"></i> ${comment.likes || 0}
                </div>
            </div>
            <div class="comment-text my-2">${comment.text}</div>
            <div class="comment-sentiment ${category}">
                <i class="fas fa-${category === 'positive' ? 'smile' : category === 'negative' ? 'frown' : 'meh'}"></i>
                ${category.charAt(0).toUpperCase() + category.slice(1)}
            </div>
        `;
        container.appendChild(commentEl);
    });
}