(function() {
    // Добавляем стили
    const style = document.createElement('style');
    style.id = 'mobile-menu-styles';
    style.textContent = `
        .mobile-menu-bottom {
            display: none;
            position: fixed;
            bottom: 20px;
            left: 0;
            right: 0;
            text-align: center;
            z-index: 1050;
        }
        
        @media (max-width: 1024px) {
            .mobile-menu-bottom {
                display: block;
            }
        }
        
        .mobile-menu-btn {
            background: var(--accent-color);
            color: white;
            border: none;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            font-size: 1.6rem;
            cursor: pointer;
            box-shadow: 0 0 15px rgba(0, 198, 255, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            transition: all 0.3s ease;
        }
        
        .mobile-menu-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 0 25px rgba(0, 198, 255, 0.7);
        }
        
        .mobile-menu-modal {
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 70vh;
            max-height: 90%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1100;
            align-items: flex-end;
            transform: translateY(100%);
            transition: transform 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
            opacity: 1;
            overflow: visible;
            padding-top: 0;
            border-radius: 30px 30px 0 0;
        }
        
        .mobile-menu-modal.open {
            transform: translateY(0);
            display: flex;
        }
        
        .mobile-menu-modal .modal-content {
            background: 
                linear-gradient(135deg, rgba(10,14,23,0.97), rgba(26,33,56,0.97)),
                repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 10px,
                    rgba(0,198,255,0.1) 10px,
                    rgba(0,198,255,0.1) 20px
                );
            border: 3px solid rgba(0, 198, 255, 0.4);
            border-radius: 30px 30px 0 0;
            box-shadow: 
                0 0 15px rgba(0, 198, 255, 0.3),
                inset 0 0 20px rgba(0, 150, 200, 0.2);
            overflow: visible;
            position: relative;
            width: 100%;
            height: 100%;
            z-index: 1;
        }

        /* Красивые линии для фона */
        .modal-content::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, transparent, #00c6ff, transparent);
            z-index: 2;
            opacity: 0.4;
        }
        
        .modal-content::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, transparent, #00c6ff, transparent);
            z-index: 2;
            opacity: 0.4;
        }
        
        .mobile-menu-modal .modal-body {
            flex: 1;
            overflow: hidden;
            padding-bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            position: relative;
            z-index: 3;
        }
        
        /* Кнопка закрытия */
        .close-modal {
            position: absolute;
            top: 15px;
            right: 15px;
            background: #ff6b6b;
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .close-modal:hover {
            background: #ff5252;
            transform: scale(1.1);
            box-shadow: 0 0 15px rgba(255, 107, 107, 0.5);
        }
        
        .floating-avatar-container {
            position: absolute;
            top: -50px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1500;
            width: 100%;
            text-align: center;
            padding-bottom: 5px;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .floating-avatar,
        .floating-avatar-info {
            pointer-events: auto;
        }
        
        .floating-avatar {
            width: 110px;
            height: 110px;
            border-radius: 50%;
            object-fit: cover;
            position: relative;
            z-index: 2;
            border: 3px solid var(--accent-color);
            box-shadow: 0 0 15px rgba(0, 198, 255, 0.5);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin: 0 auto;
            background: transparent !important;
        }
        
        .avatar-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #0a0e17, #1a2138);
            color: #ffffff;
            font-weight: bold;
            font-size: 1.5rem;
            text-align: center;
            padding: 10px;
            text-shadow: 0 0 12px rgba(0, 198, 255, 0.8);
            border-radius: 50%;
        }
        
        .user-info-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            margin-bottom: 20px;
            margin-top: 25px;
        }
        
        .floating-avatar-info {
            font-size: 1.05rem;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            overflow: visible;
            text-overflow: clip;
            width: 100%;
            box-sizing: border-box;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: none !important;
            border: none !important;
            border-radius: 0;
            box-shadow: none !important;
            text-shadow: none !important;
            padding: 0 !important;
            max-width: 250px;
            margin: 0 auto;
            min-height: auto;
            white-space: nowrap;
            line-height: 1.3;
            color: white;
        }
        
        .user-balance {
            font-size: 0.95rem;
            font-weight: 700;
            text-overflow: clip;
            background: none !important;
            border: none !important;
            border-radius: 0;
            box-shadow: none !important;
            text-shadow: none !important;
            padding: 0 !important;
            transition: all 0.3s ease;
            max-width: 180px;
            margin: 0 auto;
            margin-top: 5px;
            color: #00c6ff;
        }
        
        /* Увеличенные иконки с градиентом */
        .menu-item i {
            font-size: 38px !important;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #00c6ff, #0072ff);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 0 8px rgba(0, 198, 255, 0.3);
        }
        
        /* Убираем подчеркивание у всех ссылок */
        .menu-item a,
        .floating-avatar-info,
        .user-balance,
        .floating-avatar {
            text-decoration: none !important;
            outline: none !important;
        }
        
        /* Убираем подчеркивание при фокусе */
        .menu-item a:focus,
        .menu-item a:active {
            text-decoration: none !important;
            outline: none !important;
        }
        
        /* Убираем тень при наведении */
        .menu-item:hover {
            box-shadow: none !important;
        }
        
        /* Увеличенные ячейки сетки */
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 15px;
            width: 100%;
            max-width: 460px;
            height: 460px;
            margin: 0 auto;
            background: transparent;
            box-sizing: border-box;
            padding: 0;
            margin-top: 150px;
        }
        
        .menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 15px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 198, 255, 0.3);
            aspect-ratio: 1 / 1;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            min-width: 0;
            min-height: 0;
            padding: 12px 8px;
            box-sizing: border-box;
            color: white;
            position: relative;
            z-index: 3;
        }
        
        .menu-item:hover {
            background: rgba(0, 198, 255, 0.2);
            transform: translateY(-7px);
            border-color: var(--accent-color);
            box-shadow: none;
        }
        
        .menu-item span {
            font-size: 0.75rem;
            line-height: 1.3;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            font-weight: 500;
            word-break: break-word;
            hyphens: auto;
            padding: 0 2px;
        }
        
        /* Ограничение ширины для текста под аватаркой */
        .floating-avatar-info, .user-balance {
            max-width: 250px;
            margin: 0 auto;
        }
        
        /* Уменьшенные ячейки мобильного меню */
        @media (max-width: 768px) {
            .floating-avatar-info, .user-balance {
                max-width: 230px;
            }
            
            .menu-grid {
                gap: 12px;
                max-width: 380px;
                height: 380px;
                margin-top: 140px;
            }
            .menu-item {
                padding: 10px 6px;
            }
            .menu-item i {
                font-size: 38px !important;
                margin-bottom: 8px;
            }
            .menu-item span {
                font-size: 0.7rem;
            }
            
            .user-info-container {
                margin-top: 20px;
            }
        }
        
        @media (max-width: 576px) {
            .floating-avatar-info, .user-balance {
                max-width: 220px;
            }
            
            .menu-grid {
                gap: 10px;
                max-width: 340px;
                height: 340px;
                margin-top: 130px;
            }
            .menu-item i {
                font-size: 38px !important;
            }
            .menu-item span {
                font-size: 0.65rem;
            }
            
            .user-info-container {
                margin-top: 18px;
            }
        }
        
        @media (max-width: 400px) {
            .floating-avatar-info, .user-balance {
                max-width: 200px;
            }
            
            .menu-grid {
                gap: 8px;
                max-width: 310px;
                height: 310px;
                margin-top: 120px;
            }
            .menu-item i {
                font-size: 38px !important;
            }
            .menu-item span {
                font-size: 0.6rem;
            }
            
            .user-info-container {
                margin-top: 16px;
            }
        }
        
        @media (max-width: 340px) {
            .floating-avatar-info, .user-balance {
                max-width: 180px;
            }
            
            .menu-grid {
                gap: 6px;
                max-width: 280px;
                height: 280px;
                margin-top: 110px;
            }
            .menu-item i {
                font-size: 38px !important;
            }
            .menu-item span {
                font-size: 0.55rem;
            }
            
            .user-info-container {
                margin-top: 14px;
            }
        }
        
        @media (min-width: 769px) and (max-width: 1024px) {
            .mobile-menu-modal {
                height: 55vh;
            }
            .floating-avatar-container {
                top: -50px;
            }
            .floating-avatar {
                width: 120px;
                height: 120px;
            }
            .floating-avatar-info {
                font-size: 1.1rem;
            }
            .user-balance {
                font-size: 1rem;
            }
            .menu-grid {
                max-width: 500px;
                height: 500px;
                margin-top: 140px;
            }
            .menu-item i {
                font-size: 38px !important;
            }
            .menu-item span {
                font-size: 0.8rem;
            }
            
            .user-info-container {
                margin-top: 30px;
            }
        }
        
        /* Скрыть на ПК */
        @media (min-width: 1025px) {
            .mobile-menu-modal {
                display: none !important;
            }
            .mobile-menu-bottom {
                display: none !important;
            }
        }
        
        /* Новые стили для элементов авторизации */
        #mobileLoginRegister {
            display: block;
            margin-top: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .menu-item .menu-icon-img {
            display: block;
            width: 32px;
            height: 32px;
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 8px;
            object-fit: contain;
            object-position: center;
        }
        
        #mobileLoginRegister:hover {
            color: #00c6ff;
            transform: translateY(-2px);
        }
        
        /* НОВЫЕ СТИЛИ ДЛЯ ФОНА МИКРОСХЕМЫ И АНИМАЦИИ */
        .circuit-paths {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            pointer-events: none;
        }
        
        .circuit-path {
            stroke: rgba(0, 198, 255, 0.12);
            stroke-width: 0.8px;
            fill: none;
            z-index: 1;
            stroke-linecap: square;
            stroke-linejoin: bevel;
        }
        
        .energy-ball {
            position: absolute;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00c6ff;
            box-shadow: 0 0 10px #00c6ff, 0 0 20px #00c6ff;
            z-index: 2;
            opacity: 0.9;
            transform: translate(-50%, -50%);
        }
    `;
    document.head.appendChild(style);

    // Глобальные функции навигации
    window.goToLogin = function() {
        closeAllMobileMenus();
        setTimeout(() => {
            window.location.href = "login";
        }, 100);
    }

    window.goToDashboard = function() {
        closeAllMobileMenus();
        setTimeout(() => {
            window.location.href = "/user/dashboard";
        }, 100);
    }

    // Функция для генерации HTML пользователя
    function generateUserHTML() {
        if (window.currentUser && window.currentUser.first_name) {
            // Форматируем баланс с помощью toFixed(2)
            const formattedBalance = window.currentUser.balance.toFixed(2);
            
            return `
                <div class="floating-avatar" onclick="window.goToDashboard()">
                    <div class="avatar-placeholder" style="background-color: ${window.currentUser.avatar_color}">
                        ${window.currentUser.first_name.charAt(0)}${window.currentUser.last_name.charAt(0)}
                    </div>
                </div>
                <div class="user-info-container">
                    <div class="floating-avatar-info" onclick="window.goToDashboard()">
                        ${window.currentUser.first_name} ${window.currentUser.last_name}
                    </div>
                    <div class="user-balance" onclick="window.goToDashboard()">
                        ბალანსი: ${formattedBalance}₾
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="floating-avatar" onclick="window.goToLogin()">
                    <div class="avatar-placeholder">KODI.GE</div>
                </div>
                <div class="user-info-container">
                    <div class="floating-avatar-info" onclick="window.goToLogin()">
                        ლოგინი|რეგისტრაცია
                    </div>
                </div>
            `;
        }
    }

    // Добавление анимации микросхемы
    function initCircuitAnimation(modal) {
        const content = modal.querySelector('.modal-content');
        if (!content) return;
        
        // Удаляем старую анимацию, если есть
        const existingPaths = content.querySelector('.circuit-paths');
        if (existingPaths) existingPaths.remove();
        
        // Создаем контейнер для путей
        const pathsContainer = document.createElement('div');
        pathsContainer.className = 'circuit-paths';
        content.appendChild(pathsContainer);
        
        // Создаем SVG для путей
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 100 100');
        svg.setAttribute('preserveAspectRatio', 'none');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        pathsContainer.appendChild(svg);
        
        // Создаем пути микросхемы в стиле печатных плат
        const paths = [
            // Путь 1: Угловая трасса с переходами
            "M 0,10 L 25,10 25,30 45,30 45,10 65,10 65,30 85,30 85,10 100,10",
            
            // Путь 2: Зигзагообразная дорожка
            "M 0,90 L 20,90 20,70 40,70 40,90 60,90 60,70 80,70 80,90 100,90",
            
            // Путь 3: Диагональные переходы
            "M 0,50 L 15,50 15,35 35,35 35,50 55,50 55,65 75,65 75,50 100,50",
            
            // Путь 4: Ступенчатая структура
            "M 0,70 L 30,70 30,50 50,50 50,70 70,70 70,50 90,50 90,70 100,70",
            
            // Путь 5: Прямоугольная сетка
            "M 0,30 L 20,30 20,45 40,45 40,60 60,60 60,45 80,45 80,30 100,30",
            
            // Путь 6: Сложный маршрут с диагоналями
            "M 0,80 L 35,80 35,60 55,60 55,40 75,40 75,60 95,60 95,80 100,80"
        ];
        
        // Создаем пути в SVG
        paths.forEach((d, i) => {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            path.setAttribute('class', 'circuit-path');
            svg.appendChild(path);
        });
        
        // Создаем контейнер для шариков
        const ballsContainer = document.createElement('div');
        ballsContainer.className = 'energy-balls';
        pathsContainer.appendChild(ballsContainer);
        
        // Создаем шарики и анимируем их движение
        paths.forEach((d, i) => {
            const ball = document.createElement('div');
            ball.className = 'energy-ball';
            ballsContainer.appendChild(ball);
            
            // Анимация движения шарика
            animateBallAlongPath(ball, d, i);
        });
    }
    
    // Функция для анимации шарика вдоль пути
    function animateBallAlongPath(ball, pathData, index) {
        // Создаем временный SVG для вычисления позиций
        const svgNS = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(svgNS, 'svg');
        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('d', pathData);
        svg.appendChild(path);
        document.body.appendChild(svg);
        
        const pathLength = path.getTotalLength();
        const duration = 4000 + Math.random() * 2000;
        const delay = index * 600;
        
        let startTime = null;
        
        const animate = (timestamp) => {
            if (!startTime) startTime = timestamp;
            const elapsed = timestamp - startTime;
            const progress = (elapsed % duration) / duration;
            
            // Вычисляем позицию на пути
            const point = path.getPointAtLength(progress * pathLength);
            
            // Преобразуем координаты SVG в проценты
            const xPercent = (point.x);
            const yPercent = (point.y);
            
            // Позиционируем шарик
            ball.style.left = `${xPercent}%`;
            ball.style.top = `${yPercent}%`;
            
            // Пульсация шарика
            const pulse = 0.7 + Math.sin(elapsed / 300) * 0.3;
            ball.style.transform = `translate(-50%, -50%) scale(${pulse})`;
            
            // Эффект затухания на поворотах
            const segmentProgress = (progress * pathLength) % 20;
            ball.style.opacity = segmentProgress < 2 || segmentProgress > 18 ? '0.7' : '0.9';
            
            requestAnimationFrame(animate);
        };
        
        // Запускаем анимацию с задержкой
        setTimeout(() => {
            requestAnimationFrame(animate);
        }, delay);
        
        // Удаляем временный SVG
        setTimeout(() => {
            document.body.removeChild(svg);
        }, 100);
    }

    // Создаем HTML структуру мобильного меню
    function createMobileMenuStructure() {
        const mobileMenuContainer = document.createElement('div');
        mobileMenuContainer.id = 'mobile-menu-container';
        document.body.appendChild(mobileMenuContainer);
        
        const isDashboard = window.location.pathname.includes('dashboard');
        const userHTML = generateUserHTML();

        if (isDashboard) {
            createDashboardMobileMenu(mobileMenuContainer, userHTML);
        } else {
            createMainMobileMenu(mobileMenuContainer, userHTML);
        }
    }

    function createDashboardMobileMenu(container, userHTML) {
        container.innerHTML = `
            <div class="mobile-menu-modal" id="mobileMenuModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <button class="close-modal" onclick="closeMobileMenu()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="modal-body">
                        <div class="floating-avatar-container">
                            ${userHTML}
                        </div>
                        <div class="menu-grid">
                            <div class="menu-item" onclick="window.location.href='/'; closeAllMobileMenus();">
                                <i class="fas fa-home"></i>
                                <span>მთავარი</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/user/accounts'; closeAllMobileMenus();">
                                <i class="fas fa-wallet"></i>
                                <span>ანგარიშები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/user/history_checks'; closeAllMobileMenus();">
                                <i class="fas fa-history"></i>
                                <span>IMEI ისტორია</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/user/history_comparisons'; closeAllMobileMenus();">
                                <i class="fas fa-exchange-alt"></i>
                                <span>შედარებები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/user/settings'; closeAllMobileMenus();">
                                <i class="fas fa-cog"></i>
                                <span>პარამეტრები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/auth/logout'; closeAllMobileMenus();">
                                <i class="fas fa-sign-out-alt"></i>
                                <span>გასვლა</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Инициализируем анимацию после добавления в DOM
        setTimeout(() => {
            const modal = document.getElementById('mobileMenuModal');
            if (modal) initCircuitAnimation(modal);
        }, 50);
    }

    function createMainMobileMenu(container, userHTML) {
        container.innerHTML = `
            <!-- Mobile Menu Modal -->
            <div class="mobile-menu-modal" id="mobileMenuModal">
                <button class="close-modal" onclick="closeMobileMenu()">
                    <i class="fas fa-times"></i>
                </button>
                
                <div class="floating-avatar-container">
                    ${userHTML}
                </div>
                
                <div class="modal-content">
                    <div class="modal-body">
                        <div class="menu-grid">
                            <a class="menu-item" href="/" onclick="closeAllMobileMenus();">
                                <i class="fas fa-home"></i>
                                <span>მთავარი</span>
                            </a>
                            <div class="menu-item" onclick="openAppleSubmenu()">
                                <i class="fab fa-apple"></i>
                                <span>Apple</span>
                            </div>
                            <div class="menu-item" onclick="openAndroidSubmenu()">
                                <i class="fab fa-android"></i>
                                <span>Android</span>
                            </div>
                            <div class="menu-item disabled">
                                <i class="fas fa-unlock-alt"></i>
                                <span>განბლოკვა</span>
                            </div>
                            <a class="menu-item" href="/compare" onclick="closeAllMobileMenus();">
                                <i class="fas fa-exchange-alt"></i>
                                <span>შედარება</span>
                            </a>
                            <a class="menu-item" href="/knowledge-base" onclick="closeAllMobileMenus();">
                                <i class="fas fa-book"></i>
                                <span>ცოდნის ბაზა</span>
                            </a>
                            <a class="menu-item" href="/contacts" onclick="closeAllMobileMenus();">
                                <i class="fas fa-address-card"></i>
                                <span>კონტაქტი</span>
                            </a>
                            <div class="menu-item">
                                <i class="fas fa-shield-alt"></i>
                                <span>კონფიდენციალურობა</span>
                            </div>
                            <div class="menu-item">
                                <i class="fas fa-undo"></i>
                                <span>დაბრუნება</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Apple Submenu Modal -->
            <div class="mobile-menu-modal" id="appleSubmenuModal">
                <button class="close-modal" onclick="closeAppleSubmenu()">
                    <i class="fas fa-times"></i>
                </button>

                <div class="floating-avatar-container">
                    ${userHTML}
                </div>
                
                <div class="modal-content">
                    <div class="modal-body">
                        <div class="menu-grid">
                            <a class="menu-item" href="/applecheck?type=free" onclick="closeAllMobileMenus();">
                                <img src="static/ico/8f1197c9-19f4-4923-8030-4f7b88c9d697_20250627_012614_0000.png" 
                                     class="menu-icon-img">
                                <span>უფასო შემოწმება</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=fmi" onclick="closeAllMobileMenus();">
                                <img src="static/ico/f9a07c0e-e427-4a1a-aab9-948ba60f1b6a_20250627_012716_0000.png" 
                                     class="menu-icon-img">
                                <span>FMI iCloud</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=sim_lock" onclick="closeAllMobileMenus();">
                                <img src="static/ico/957afe67-7a27-48cb-9622-6c557b220b71_20250627_012808_0000.png" 
                                     class="menu-icon-img">
                                <span>SIM ლოკი</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=blacklist" onclick="closeAllMobileMenus();">
                                <img src="static/ico/4e28c4f2-541b-4a1b-8163-c79e6db5481c_20250627_012852_0000.png" 
                                     class="menu-icon-img">
                                <span>შავი სია</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=mdm" onclick="closeAllMobileMenus();">
                                <img src="static/ico/275e6a62-c55e-48b9-8781-5b323ebcdce0_20250627_012946_0000.png" 
                                     class="menu-icon-img">
                                <span>MDM ბლოკი</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=premium" onclick="closeAllMobileMenus();">
                                <img src="static/ico/84df4824-0564-447c-b5c4-e749442bdc19_20250627_013110_0000.png" 
                                     class="menu-icon-img">
                                <span>პრემიუმ შემოწმება</span>
                            </a>
                            <a class="menu-item" href="#" onclick="alert('სერვისი მომზადების პროცესშია'); closeAllMobileMenus();">
                                <img src="static/ico/874fae5b-c0f5-42d8-9c37-679aa86360e6_20250627_013030_0000.png" 
                                     class="menu-icon-img">
                                <span>MacBook</span>
                            </a>
                            <div class="menu-item" onclick="closeAppleSubmenu()">
                                <i class="fas fa-arrow-left"></i>
                                <span>უკან</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Android Submenu Modal -->
            <div class="mobile-menu-modal" id="androidSubmenuModal">
                <button class="close-modal" onclick="closeAndroidSubmenu()">
                    <i class="fas fa-times"></i>
                </button>

                <div class="floating-avatar-container">
                    ${userHTML}
                </div>
                
                <div class="modal-content">
                    <div class="modal-body">
                        <div class="menu-grid">
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fab fa-samsung"></i>
                                <span>Samsung</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fas fa-bolt"></i>
                                <span>Xiaomi</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fab fa-google"></i>
                                <span>Pixel</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fab fa-huawei"></i>
                                <span>Huawei</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fas fa-circle"></i>
                                <span>Oppo</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fab fa-android"></i>
                                <span>LG</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                                <i class="fas fa-ellipsis-h"></i>
                                <span>სხვა</span>
                            </a>
                            <div class="menu-item" onclick="closeAndroidSubmenu()">
                                <i class="fas fa-arrow-left"></i>
                                <span>უკან</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Инициализируем анимацию для всех модальных окон
        setTimeout(() => {
            const modal = document.getElementById('mobileMenuModal');
            if (modal) initCircuitAnimation(modal);
            
            const appleModal = document.getElementById('appleSubmenuModal');
            if (appleModal) initCircuitAnimation(appleModal);
            
            const androidModal = document.getElementById('androidSubmenuModal');
            if (androidModal) initCircuitAnimation(androidModal);
        }, 50);
    }

    // Mobile menu functions
    window.openMobileMenu = function() {
        try {
            const modal = document.getElementById('mobileMenuModal');
            if (modal) {
                modal.style.display = 'flex';
                setTimeout(() => {
                    modal.classList.add('open');
                }, 10);
            }
        } catch(e) {
            console.error('Error opening mobile menu:', e);
        }
    }

    window.closeMobileMenu = function() {
        try {
            const modal = document.getElementById('mobileMenuModal');
            if (modal) {
                modal.classList.remove('open');
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 400);
            }
        } catch(e) {
            console.error('Error closing mobile menu:', e);
        }
    }

    window.openAppleSubmenu = function() {
        try {
            closeMobileMenu();
            const appleModal = document.getElementById('appleSubmenuModal');
            if (appleModal) {
                appleModal.style.display = 'flex';
                setTimeout(() => {
                    appleModal.classList.add('open');
                }, 10);
            }
        } catch(e) {
            console.error('Error opening Apple submenu:', e);
        }
    }

    window.closeAppleSubmenu = function() {
        try {
            const appleModal = document.getElementById('appleSubmenuModal');
            if (appleModal) {
                appleModal.classList.remove('open');
                setTimeout(() => {
                    appleModal.style.display = 'none';
                    openMobileMenu();
                }, 400);
            }
        } catch(e) {
            console.error('Error closing Apple submenu:', e);
        }
    }

    window.openAndroidSubmenu = function() {
        try {
            closeMobileMenu();
            const androidModal = document.getElementById('androidSubmenuModal');
            if (androidModal) {
                androidModal.style.display = 'flex';
                setTimeout(() => {
                    androidModal.classList.add('open');
                }, 10);
            }
        } catch(e) {
            console.error('Error opening Android submenu:', e);
        }
    }

    window.closeAndroidSubmenu = function() {
        try {
            const androidModal = document.getElementById('androidSubmenuModal');
            if (androidModal) {
                androidModal.classList.remove('open');
                setTimeout(() => {
                    androidModal.style.display = 'none';
                    openMobileMenu();
                }, 400);
            }
        } catch(e) {
            console.error('Error closing Android submenu:', e);
        }
    }

    window.closeAllMobileMenus = function() {
        closeMobileMenu();
        closeAppleSubmenu();
        closeAndroidSubmenu();
    }

    // Initialize mobile menu when the page loads
    document.addEventListener('DOMContentLoaded', () => {
        // Создаем структуру меню
        createMobileMenuStructure();
        
        // Mobile menu button setup
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', function() {
                // Пересоздаем меню для обновления данных пользователя
                const container = document.getElementById('mobile-menu-container');
                if (container) {
                    container.remove();
                }
                createMobileMenuStructure();
                openMobileMenu();
            });
        } else {
            console.warn('Mobile menu button not found');
        }

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            try {
                const mobileMenuModal = document.getElementById('mobileMenuModal');
                const appleSubmenuModal = document.getElementById('appleSubmenuModal');
                const androidSubmenuModal = document.getElementById('androidSubmenuModal');
                const floatingAvatar = document.querySelector('.floating-avatar-container');
                
                // Close mobile menu if click is outside
                if (mobileMenuModal && mobileMenuModal.classList.contains('open') && 
                    !mobileMenuModal.contains(e.target) && 
                    e.target.id !== 'mobileMenuBtn' &&
                    !(floatingAvatar && floatingAvatar.contains(e.target))) {
                    closeMobileMenu();
                }
                
                // Close apple submenu if click is outside
                if (appleSubmenuModal && appleSubmenuModal.classList.contains('open') && 
                    !appleSubmenuModal.contains(e.target) && 
                    e.target.id !== 'mobileMenuBtn') {
                    closeAppleSubmenu();
                }
                
                // Close android submenu if click is outside
                if (androidSubmenuModal && androidSubmenuModal.classList.contains('open') && 
                    !androidSubmenuModal.contains(e.target) && 
                    e.target.id !== 'mobileMenuBtn') {
                    closeAndroidSubmenu();
                }
            } catch(e) {
                console.error('Click handler error:', e);
            }
        });
    });
})();
