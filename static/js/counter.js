// counter.js - функционал счетчика проверок со стилями
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
    
    decrement() {
        this.value--;
        this.render();
        return this.value;
    }
    
    setValue(value) {
        this.value = value;
        this.render();
        return this.value;
    }
    
    getValue() {
        return this.value;
    }
    
    render() {
        if (this.element) {
            this.element.textContent = this.value.toLocaleString();
        }
    }
}

// Добавляем стили для счетчика
const counterStyles = document.createElement('style');
counterStyles.textContent = `
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 40px;
    }
    
    .stat-card {
        background: linear-gradient(135deg, rgba(26, 33, 56, 0.7), rgba(10, 14, 23, 0.9));
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        position: relative;
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
document.head.appendChild(counterStyles);

// Инициализация счетчиков
const dailyCounter = new Counter('daily-checks', 125);
const weeklyCounter = new Counter('weekly-checks', 875);
const monthlyCounter = new Counter('monthly-checks', 3750);

// Функция для обновления всех счетчиков
function incrementCounters() {
    dailyCounter.increment();
    weeklyCounter.increment();
    monthlyCounter.increment();
    
    // Сохранение в localStorage
    localStorage.setItem('statsData', JSON.stringify({
        daily: dailyCounter.getValue(),
        weekly: weeklyCounter.getValue(),
        monthly: monthlyCounter.getValue()
    }));
}

// Создаем HTML структуру для счетчиков
function createStatsContainer() {
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
    
    return statsContainer;
}

// Загрузка данных из localStorage
document.addEventListener('DOMContentLoaded', () => {
    // Добавляем контейнер счетчиков в DOM
    const mainContent = document.querySelector('.main-content');
    const pricingSection = document.getElementById('pricing');
    
    if (mainContent && pricingSection) {
        const statsContainer = createStatsContainer();
        mainContent.insertBefore(statsContainer, pricingSection.nextSibling);
    }
    
    // Загружаем сохраненные значения
    const savedStats = localStorage.getItem('statsData');
    if (savedStats) {
        const stats = JSON.parse(savedStats);
        dailyCounter.setValue(stats.daily);
        weeklyCounter.setValue(stats.weekly);
        monthlyCounter.setValue(stats.monthly);
    }
});
