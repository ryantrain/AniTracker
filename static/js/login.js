// Load PapaParse dynamically (no HTML changes required)
function loadPapa() {
    if (window.Papa) return Promise.resolve(window.Papa);
    return new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/papaparse@5.5.3/papaparse.min.js';
        s.async = true;
        s.onload = () => resolve(window.Papa);
        s.onerror = () => reject(new Error('Failed to load PapaParse'));
        document.head.appendChild(s);
    });
}

(async function init() {
    try {
        await loadPapa();
    } catch (err) {
        console.error('Failed to load PapaParse', err);
        return;
    }

    const user = document.getElementById('username');
    const pass = document.getElementById('password');
    const loginBtn = document.getElementById('login-button');

    if (!loginBtn) return;

    loginBtn.addEventListener('click', function(event) {
        event.preventDefault();

        const username = user ? user.value : '';
        const password = pass ? pass.value : '';

        const csvUrl = (window.USER_CSV_URL && String(window.USER_CSV_URL).trim()) || '/static/sensitive/user-info.csv';

        Papa.parse(csvUrl, {
            download: true,
            header: false,
            complete: function(results){
                const rows = (results.data || []).filter(Boolean);
                for (const row of rows) {
                    if (row[0] === username && row[1] === password) {
                        window.location.href = '/';
                        return;
                    }
                }
            alert('Invalid username or password');
            }
        })
    });
})
();