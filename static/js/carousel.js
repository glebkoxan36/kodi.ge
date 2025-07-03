document.addEventListener('DOMContentLoaded', function() {
    // Добавляем стили для карусели и заглушки
    const style = document.createElement('style');
    style.textContent = `
        /* Основные стили карусели */
        .carousel {
            position: relative;
            max-width: 1000px;
            margin: 30px auto;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            border-radius: 12px;
            min-height: 500px;
            background: #000;
        }
        .carousel-inner {
            display: flex;
            transition: transform 0.7s cubic-bezier(0.33, 1, 0.68, 1);
            height: 100%;
        }
        .slide {
            min-width: 100%;
            box-sizing: border-box;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .slide img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .carousel-nav {
            position: absolute;
            top: 50%;
            width: 100%;
            display: flex;
            justify-content: space-between;
            transform: translateY(-50%);
            z-index: 20;
            pointer-events: none;
        }
        .carousel-btn {
            background: rgba(0,0,0,0.6);
            color: white;
            border: none;
            padding: 15px 20px;
            cursor: pointer;
            font-size: 24px;
            transition: all 0.3s;
            pointer-events: all;
            backdrop-filter: blur(3px);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .carousel-btn:hover {
            background: rgba(0,0,0,0.9);
            transform: scale(1.1);
        }
        .prev-btn {
            border-radius: 0 8px 8px 0;
        }
        .next-btn {
            border-radius: 8px 0 0 8px;
        }
        .carousel-pagination {
            position: absolute;
            bottom: 20px;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            gap: 12px;
            z-index: 20;
        }
    .carousel {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    margin: 30px auto;
    max-width: 1000px;
    min-height: 500px;
}
        .pagination-dot {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: rgba(255,255,255,0.4);
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid rgba(0,0,0,0.3);
        }
        .pagination-dot:hover {
            transform: scale(1.3);
        }
        .pagination-dot.active {
            background: white;
            transform: scale(1.2);
            box-shadow: 0 0 8px rgba(255,255,255,0.8);
        }
        
        /* Стили для заглушки */
        .ad-placeholder {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            color: white;
            font-family: 'Montserrat', 'Arial', sans-serif;
            text-align: center;
            padding: 30px;
            z-index: 10;
            overflow: hidden;
        }
        .ad-text {
            font-size: 32px;
            margin: 30px 0;
            z-index: 15;
            text-shadow: 0 3px 10px rgba(0,0,0,0.7);
            font-weight: 600;
            letter-spacing: 1px;
            max-width: 80%;
            line-height: 1.4;
        }
        .logo-container {
            width: 180px;
            height: 180px;
            z-index: 15;
            filter: drop-shadow(0 5px 15px rgba(0,0,0,0.5));
        }
        .logo-svg {
            width: 100%;
            height: 100%;
            animation: floatLogo 8s ease-in-out infinite;
        }
        .circles-container {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 12;
            opacity: 0.25;
        }
        .circle {
            position: absolute;
            border-radius: 50%;
            animation: float 25s infinite linear;
            filter: blur(1px);
        }
        
        /* Анимации */
        @keyframes float {
            0% {
                transform: translate(0, 0) rotate(0deg);
            }
            25% {
                transform: translate(5%, 15%) rotate(90deg);
            }
            50% {
                transform: translate(10%, 5%) rotate(180deg);
            }
            75% {
                transform: translate(5%, 12%) rotate(270deg);
            }
            100% {
                transform: translate(0, 0) rotate(360deg);
            }
        }
        @keyframes floatLogo {
            0% {
                transform: translateY(0) rotate(0deg);
            }
            25% {
                transform: translateY(-10px) rotate(2deg);
            }
            50% {
                transform: translateY(0) rotate(0deg);
            }
            75% {
                transform: translateY(-7px) rotate(-2deg);
            }
            100% {
                transform: translateY(0) rotate(0deg);
            }
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.05); opacity: 1; }
            100% { transform: scale(1); opacity: 0.8; }
        }
        
        /* Адаптивность */
        @media (max-width: 768px) {
            .carousel {
                min-height: 400px;
                max-width: 95%;
            }
            .ad-text {
                font-size: 24px;
            }
            .logo-container {
                width: 140px;
                height: 140px;
            }
            .carousel-btn {
                padding: 12px 15px;
                font-size: 20px;
            }
        }
    `;
    document.head.appendChild(style);

    // Логика карусели
    class Carousel {
        constructor(containerId) {
            this.container = document.getElementById(containerId);
            this.slidesContainer = this.container.querySelector('.carousel-inner');
            this.slides = this.container.querySelectorAll('.slide');
            this.currentIndex = 0;
            
            // Проверяем изображения и добавляем заглушки
            this.checkImages();
            
            // Создаем элементы управления
            this.createNavigation();
            this.createPagination();
            
            // Инициализация
            this.updateCarousel();
            
            // Автопрокрутка
            this.autoPlay();
        }

        checkImages() {
            this.slides.forEach(slide => {
                const img = slide.querySelector('img');
                if (!img || !img.complete || img.naturalHeight === 0) {
                    this.createPlaceholder(slide);
                } else {
                    img.onerror = () => this.createPlaceholder(slide);
                }
            });
        }

        createPlaceholder(slide) {
            // Удаляем битое изображение, если есть
            const img = slide.querySelector('img');
            if (img) img.remove();
            
            // Проверяем, не добавлена ли уже заглушка
            if (slide.querySelector('.ad-placeholder')) return;
            
            // Создаем контейнер для заглушки
            const placeholder = document.createElement('div');
            placeholder.className = 'ad-placeholder';
            
            // Добавляем анимированное лого и текст
            placeholder.innerHTML = `
                <div class="logo-container">
                    <svg class="logo-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#ff9a9e" />
                                <stop offset="50%" stop-color="#fad0c4" />
                                <stop offset="100%" stop-color="#a1c4fd" />
                            </linearGradient>
                            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                                <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
                                <feFlood flood-color="#a1c4fd" result="glowColor" />
                                <feComposite in="glowColor" in2="blur" operator="in" result="glow" />
                                <feBlend in="SourceGraphic" in2="glow" mode="screen" />
                            </filter>
                        </defs>
                        
                        <circle cx="100" cy="100" r="90" fill="url(#grad1)" filter="url(#glow)" />
                        <path d="M80,70 L120,70 L140,100 L120,130 L80,130 L60,100 Z" fill="white" />
                        <circle cx="100" cy="100" r="30" fill="#0f0c29" />
                        <text x="100" y="105" text-anchor="middle" fill="white" font-size="24" font-weight="bold">G</text>
                        
                        <animateTransform 
                            attributeName="transform" 
                            type="rotate" 
                            from="0 100 100" 
                            to="360 100 100" 
                            dur="20s" 
                            repeatCount="indefinite" 
                        />
                    </svg>
                </div>
                <div class="ad-text">აქ უნდა იყოს თქვენი რეკლამა</div>
                <div class="circles-container"></div>
            `;
            
            // Добавляем анимированные круги
            this.createFloatingCircles(placeholder.querySelector('.circles-container'));
            
            slide.appendChild(placeholder);
        }

        createFloatingCircles(container) {
            const colors = ['#ff9a9e', '#fad0c4', '#a1c4fd', '#c2e9fb', '#ffecd2', '#d4fc79'];
            const count = 18;
            
            for (let i = 0; i < count; i++) {
                const circle = document.createElement('div');
                circle.className = 'circle';
                
                // Случайный размер
                const size = Math.random() * 100 + 30;
                circle.style.width = `${size}px`;
                circle.style.height = `${size}px`;
                
                // Случайный цвет
                circle.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                circle.style.opacity = Math.random() * 0.6 + 0.2;
                
                // Случайная позиция
                circle.style.left = `${Math.random() * 100}%`;
                circle.style.top = `${Math.random() * 100}%`;
                
                // Случайная задержка анимации
                circle.style.animationDelay = `${Math.random() * 10}s`;
                
                // Случайная скорость анимации
                circle.style.animationDuration = `${25 + Math.random() * 20}s`;
                
                container.appendChild(circle);
            }
        }

        createNavigation() {
            const navContainer = document.createElement('div');
            navContainer.className = 'carousel-nav';
            
            this.prevBtn = document.createElement('button');
            this.prevBtn.className = 'carousel-btn prev-btn';
            this.prevBtn.innerHTML = '❮';
            this.prevBtn.setAttribute('aria-label', 'Previous slide');
            
            this.nextBtn = document.createElement('button');
            this.nextBtn.className = 'carousel-btn next-btn';
            this.nextBtn.innerHTML = '❯';
            this.nextBtn.setAttribute('aria-label', 'Next slide');
            
            navContainer.append(this.prevBtn, this.nextBtn);
            this.container.appendChild(navContainer);
            
            // Обработчики событий
            this.prevBtn.addEventListener('click', () => this.prevSlide());
            this.nextBtn.addEventListener('click', () => this.nextSlide());
        }

        createPagination() {
            this.paginationContainer = document.createElement('div');
            this.paginationContainer.className = 'carousel-pagination';
            
            this.dots = [];
            this.slides.forEach((_, i) => {
                const dot = document.createElement('div');
                dot.className = 'pagination-dot';
                dot.setAttribute('role', 'button');
                dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
                if (i === this.currentIndex) dot.classList.add('active');
                this.paginationContainer.appendChild(dot);
                this.dots.push(dot);
                
                dot.addEventListener('click', () => this.goToSlide(i));
            });
            
            this.container.appendChild(this.paginationContainer);
        }

        updateCarousel() {
            this.slidesContainer.style.transform = `translateX(-${this.currentIndex * 100}%)`;
            
            // Обновляем активную точку
            this.dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === this.currentIndex);
            });
        }

        nextSlide() {
            this.currentIndex = (this.currentIndex + 1) % this.slides.length;
            this.updateCarousel();
            this.resetAutoPlay();
        }

        prevSlide() {
            this.currentIndex = (this.currentIndex - 1 + this.slides.length) % this.slides.length;
            this.updateCarousel();
            this.resetAutoPlay();
        }

        goToSlide(index) {
            if (index >= 0 && index < this.slides.length) {
                this.currentIndex = index;
                this.updateCarousel();
                this.resetAutoPlay();
            }
        }
        
        autoPlay() {
            this.interval = setInterval(() => {
                this.nextSlide();
            }, 5000);
        }
        
        resetAutoPlay() {
            clearInterval(this.interval);
            this.autoPlay();
        }
    }

    // Инициализация карусели
    new Carousel('carousel-container');
});
