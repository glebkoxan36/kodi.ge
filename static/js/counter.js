// static/js/counter.js
document.addEventListener('DOMContentLoaded', () => {
    // Создаем стили для счетчиков
    const style = document.createElement('style');
    style.textContent = `
        .stats-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        
        .stat-card {
            background: linear-gradient(135deg, rgba(26, 33, 56, 0.7), rgba(10, 14, 23, 0.9));
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.05);
            position: relative;
            animation: cardAppear 0.6s ease-out;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: 12px;
            box-shadow: 0 0 15px rgba(0, 198, 255, 0.3);
            opacity: 0.8;
            animation: neonGlow 3s infinite alternate;
            pointer-events: none;
            z-index: 0;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 10px 0;
            color: #00c6ff;
        }
        
        .stat-label {
            font-size: 1rem;
            color: #c0c0d0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        @keyframes neonGlow {
            0% {
                box-shadow: 0 0 10px rgba(0, 198, 255, 0.4);
            }
            50% {
                box-shadow: 0 0 25px rgba(0, 198, 255, 0.7);
            }
            100% {
                box-shadow: 0 0 15px rgba(0, 198, 255, 0.5);
            }
        }
    `;
    document.head.appendChild(style);

    // Создаем структуру счетчиков
    const statsContainer = document.createElement('div');
    statsContainer.className = 'stats-container';
    statsContainer.innerHTML = `
        <div class="stat-card">
            <i class="fas fa-sync fa-2x"></i>
            <div class="stat-value" id="daily-checks">0</div>
            <div class="stat-label">შემოწმება დღეში</div>
        </div>
        <div class="stat-card">
            <i class="fas fa-calendar-week fa-2x"></i>
            <div class="stat-value" id="weekly-checks">0</div>
            <div class="stat-label">შემოწმება კვირაში</div>
        </div>
        <div class="stat-card">
            <i class="fas fa-calendar-alt fa-2x"></i>
            <div class="stat-value" id="monthly-checks">0</div>
            <div class="stat-label">შემოწმება თვეში</div>
        </div>
    `;

    // Вставляем контейнер в DOM
    const container = document.getElementById('stats-container');
    if (container) {
        container.appendChild(statsContainer);
    } else {
        // Если контейнер не найден, вставляем в конец main-content
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.appendChild(statsContainer);
        }
    }

    // Класс Counter
    class Counter {
        constructor(elementId, initialValue = 0) {
            this.element = document.getElementById(elementId);
            this.value = initialValue;
            this.render();
        }
        
        increment() {
            this.value++;
            this.render();
            return this.value;
        }
        
        setValue(value) {
            this.value = value;
            this.render();
            return this.value;
        }
        
        render() {
            if (this.element) {
                this.element.textContent = this.value.toLocaleString();
            }
        }
    }

    // Инициализация счетчиков
    const dailyCounter = new Counter('daily-checks', 0);
    const weeklyCounter = new Counter('weekly-checks', 0);
    const monthlyCounter = new Counter('monthly-checks', 0);

    // Функция для обновления счетчиков
    function updateCounters() {
        fetch('/api/get_counters')
            .then(response => response.json())
            .then(data => {
                dailyCounter.setValue(data.daily);
                weeklyCounter.setValue(data.weekly);
                monthlyCounter.setValue(data.monthly);
            })
            .catch(error => console.error('Error loading counters:', error));
    }

    // Первоначальное обновление
    updateCounters();
    
    // Обновляем каждые 30 секунд
    setInterval(updateCounters, 30000);
});
