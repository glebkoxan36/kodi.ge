// counter.js - функционал счетчика проверок
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

// Загрузка данных из localStorage
document.addEventListener('DOMContentLoaded', () => {
    const savedStats = localStorage.getItem('statsData');
    if (savedStats) {
        const stats = JSON.parse(savedStats);
        dailyCounter.setValue(stats.daily);
        weeklyCounter.setValue(stats.weekly);
        monthlyCounter.setValue(stats.monthly);
    }
});

// Экспорт для использования в других модулях
export { dailyCounter, weeklyCounter, monthlyCounter, incrementCounters };
