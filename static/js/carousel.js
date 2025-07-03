document.addEventListener('DOMContentLoaded', function() {
    const carouselContainer = document.getElementById('carousel-container');
    if (!carouselContainer) return;
    
    // Создаем стили для карусели
    const style = document.createElement('style');
    style.textContent = `
        .carousel-inner {
            transition: transform 0.7s cubic-bezier(0.33, 1, 0.68, 1);
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
            z-index: 30;
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
        }
        .ad-text {
            font-size: 24px;
            margin: 20px 0;
            z-index: 15;
            text-shadow: 0 3px 10px rgba(0,0,0,0.7);
            font-weight: 600;
            letter-spacing: 1px;
            max-width: 90%;
            line-height: 1.4;
        }
        .logo-container {
            width: 120px;
            height: 120px;
            z-index: 15;
            filter: drop-shadow(0 5px 15px rgba(0,0,0,0.5));
        }
        .logo-svg {
            width: 100%;
            height: 100%;
            animation: floatLogo 8s ease-in-out infinite;
        }
        
        /* Анимации */
        @keyframes floatLogo {
            0% { transform: translateY(0) rotate(0deg); }
            25% { transform: translateY(-10px) rotate(2deg); }
            50% { transform: translateY(0) rotate(0deg); }
            75% { transform: translateY(-7px) rotate(-2deg); }
            100% { transform: translateY(0) rotate(0deg); }
        }
        
        /* Адаптивность */
        @media (max-width: 768px) {
            .carousel-btn { padding: 12px 15px; font-size: 20px; }
            .ad-text { font-size: 20px; }
            .logo-container { width: 100px; height: 100px; }
        }
    `;
    document.head.appendChild(style);

    // Логика карусели
    class Carousel {
        constructor(container) {
            this.container = container;
            this.slidesContainer = container.querySelector('.carousel-inner');
            this.slides = Array.from(container.querySelectorAll('.slide'));
            this.currentIndex = 0;
            this.interval = null;
            
            this.init();
        }
        
        init() {
            this.checkImages();
            this.createNavigation();
            this.createPagination();
            this.update();
            this.startAutoPlay();
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
            if (slide.querySelector('.ad-placeholder')) return;
            
            const placeholder = document.createElement('div');
            placeholder.className = 'ad-placeholder';
            placeholder.innerHTML = `
                <div class="logo-container">
                    <svg class="logo-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#ff9a9e" />
                                <stop offset="50%" stop-color="#fad0c4" />
                                <stop offset="100%" stop-color="#a1c4fd" />
                            </linearGradient>
                        </defs>
                        <circle cx="100" cy="100" r="90" fill="url(#grad1)" />
                        <path d="M80,70 L120,70 L140,100 L120,130 L80,130 L60,100 Z" fill="white" />
                        <circle cx="100" cy="100" r="30" fill="#0f0c29" />
                        <text x="100" y="105" text-anchor="middle" fill="white" font-size="24" font-weight="bold">K</text>
                    </svg>
                </div>
                <div class="ad-text">აქ უნდა იყოს თქვენი რეკლამა</div>
            `;
            
            slide.appendChild(placeholder);
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
        
        update() {
            this.slidesContainer.style.transform = `translateX(-${this.currentIndex * 100}%)`;
            this.dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === this.currentIndex);
            });
        }
        
        nextSlide() {
            this.currentIndex = (this.currentIndex + 1) % this.slides.length;
            this.update();
            this.resetAutoPlay();
        }
        
        prevSlide() {
            this.currentIndex = (this.currentIndex - 1 + this.slides.length) % this.slides.length;
            this.update();
            this.resetAutoPlay();
        }
        
        goToSlide(index) {
            if (index >= 0 && index < this.slides.length) {
                this.currentIndex = index;
                this.update();
                this.resetAutoPlay();
            }
        }
        
        startAutoPlay() {
            this.interval = setInterval(() => {
                this.nextSlide();
            }, 5000);
        }
        
        resetAutoPlay() {
            clearInterval(this.interval);
            this.startAutoPlay();
        }
    }

    // Инициализация карусели
    new Carousel(carouselContainer);
});
