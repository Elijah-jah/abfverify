{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Too Many Requests | ABFverify</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        :root {
            --bg: #f0f4ff;
            --card: #ffffff;
            --text: #1a1a2e;
            --blue: #0d6efd;
            --danger: #dc3545;
        }
        body.dark, html[data-theme="dark"] body {
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f1f5f9;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            transition: background 0.3s ease, color 0.3s ease;
        }
        .box {
            background: var(--card);
            padding: 3rem 2.5rem;
            border-radius: 20px;
            text-align: center;
            max-width: 420px;
            width: 100%;
            box-shadow: 0 25px 80px rgba(0,0,0,0.12);
            border: 2px solid var(--blue);
            animation: popIn 0.4s ease;
        }
        @keyframes popIn {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
        .icon {
            font-size: 4rem;
            color: var(--danger);
            margin-bottom: 1rem;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        h1 { font-size: 1.6rem; margin-bottom: 0.5rem; font-weight: 800; }
        p { color: #64748b; margin-bottom: 1.75rem; line-height: 1.6; font-size: 0.95rem; }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--blue);
            color: #fff;
            padding: 0.85rem 2rem;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(13,110,253,0.3); }
    </style>
</head>
<body>
    <div class="box">
        <div class="icon"><i class="fa-solid fa-shield-halved"></i></div>
        <h1>Too Many Requests</h1>
        <p>You've made too many requests in a short time. Please wait a few minutes and try again.</p>
        <a href="{% url 'login' %}" class="btn"><i class="fa-solid fa-arrow-left"></i> Back to Login</a>
    </div>
</body>
</html>