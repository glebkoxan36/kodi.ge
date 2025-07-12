(function() {
    // Кеширование DOM элементов и пользовательских данных
    let cachedElements = {};
    let userHTMLCache = null;
    
    // Функция для получения элементов с кешированием
    function getElement(id) {
        if (!cachedElements[id]) {
            cachedElements[id] = document.getElementById(id);
        }
        return cachedElements[id];
    }

    // Добавляем стили
    const style = document.createElement('style');
    style.id = 'mobile-menu-styles';
    style.textContent = `
        /* АНИМАЦИИ */
        @keyframes circuitMove {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-60px, -60px); }
        }
        
        @keyframes particle-float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(40px, -30px) scale(1.2); }
        }
        
        /* Анимированный хай-тек фон */
        .tech-background {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            overflow: hidden;
            border-radius: 30px 30px 0 0;
        }
        
        .circuit-layer {
            position: absolute;
            width: 200%;
            height: 200%;
            background-image: 
                linear-gradient(rgba(0, 198, 255, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 198, 255, 0.1) 1px, transparent 1px);
            background-size: 60px 60px;
            animation: circuitMove 40s infinite linear;
            opacity: 0.7;
            will-change: transform;
            backface-visibility: hidden;
        }
        
        .particle {
            position: absolute;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(0,198,255,0.8), transparent 70%);
            filter: blur(15px);
            animation: particle-float 25s infinite ease-in-out;
            will-change: transform;
            backface-visibility: hidden;
        }
        
        .p1 { 
            width: 150px; 
            height: 150px;
            top: 20%; 
            left: 10%;
            animation-delay: 0s;
        }
        
        .p2 { 
            width: 200px; 
            height: 200px;
            bottom: 15%; 
            right: 10%;
            animation-delay: -8s;
        }
        
        .grid-matrix {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                repeating-linear-gradient(
                    0deg,
                    transparent,
                    transparent 19px,
                    rgba(0, 114, 255, 0.05) 20px
                ),
                repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 19px,
                    rgba(0, 114, 255, 0.05) 20px
                );
            box-shadow: 
                inset 0 0 100px rgba(0, 82, 204, 0.2),
                0 0 50px rgba(0, 92, 230, 0.1);
        }
        
        /* ИСПРАВЛЕНИЯ ДЛЯ АВАТАРКИ */
        .floating-avatar-container {
            position: absolute;
            top: -50px; /* Уменьшен отступ сверху */
            left: 50%;
            transform: translateX(-50%);
            z-index: 10070;
            width: 100%;
            text-align: center;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .mobile-menu-modal .modal-content {
            padding-top: 70px; /* Уменьшен паддинг */
            position: relative;
            overflow: visible; /* Разрешаем выход за границы */
            max-height: 60vh !important; /* Максимальная высота */
            height: auto;
        }
        
        /* Остальные стили меню */
        .mobile-menu-bottom {
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            z-index: 10050;
            padding-bottom: env(safe-area-inset-bottom, 10px);
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
            margin-bottom: 10px;
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
            height: auto;
            max-height: 60vh; /* Фиксированная максимальная высота */
            z-index: 10060;
            align-items: flex-end;
            transform: translateY(100%);
            transition: transform 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
            opacity: 1;
            overflow: visible;
            padding-top: 0;
            border-radius: 30px 30px 0 0;
            padding-bottom: env(safe-area-inset-bottom, 0);
            box-sizing: border-box;
        }
        
        .mobile-menu-modal.open {
            transform: translateY(0);
            display: flex;
        }
        
        .mobile-menu-modal .modal-content {
            background: linear-gradient(135deg, #0a0e17 0%, #0a1a2a 100%);
            border: 3px solid rgba(0, 198, 255, 0.4);
            border-radius: 30px 30px 0 0;
            box-shadow: 
                0 0 15px rgba(0, 198, 255, 0.3),
                inset 0 0 20px rgba(0, 150, 200, 0.2);
            overflow: hidden;
            width: 100%;
            height: 100%;
            z-index: 1;
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
        
        .floating-avatar,
        .floating-avatar-info {
            pointer-events: auto;
        }
        
        .floating-avatar {
            width: 100px;
            height: 100px;
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
        
        .avatar-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 50%;
        }
        
        .avatar-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            background: rgba(10, 14, 23, 0.8);
            color: #ffffff;
            font-weight: bold;
            font-size: 1.2rem;
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
            margin-bottom: 15px;
            margin-top: 20px;
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
        
        .floating-avatar-info.not-logged-in {
            text-shadow: 0 0 5px #00c6ff, 0 0 10px #00c6ff;
            margin-top: 10px;
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
        
        /* Увеличенные иконки одного размера */
        .menu-item i {
            font-size: 40px !important;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #00c6ff, #0072ff);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 0 8px rgba(0, 198, 255, 0.3);
        }
        
        .menu-icon-img {
            display: block;
            width: 40px !important;
            height: 40px !important;
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 7px;
            object-fit: contain;
            object-position: center;
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
            gap: 12px;
            width: 100%;
            max-width: 440px;
            height: 440px;
            margin: 0 auto;
            background: transparent;
            box-sizing: border-box;
            padding: 0;
            margin-top: 20px;
        }
        
        .menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 15px;
            background: rgba(26, 33, 56, 0.7);
            border: 1px solid rgba(0, 198, 255, 0.4);
            aspect-ratio: 1 / 1;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 
                0 4px 12px rgba(0, 0, 0, 0.3),
                inset 0 0 10px rgba(0, 198, 255, 0.1);
            min-width: 0;
            min-height: 0;
            padding: 12px 8px;
            box-sizing: border-box;
            color: white;
            position: relative;
            z-index: 3;
            backdrop-filter: blur(2px);
        }
        
        .menu-item:hover {
            background: rgba(34, 48, 86, 0.8);
            transform: translateY(-7px);
            border-color: var(--accent-color);
            box-shadow: 
                0 6px 16px rgba(0, 0, 0, 0.4),
                inset 0 0 15px rgba(0, 198, 255, 0.2);
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
            .floating-avatar-container {
                top: -40px; /* Уменьшен отступ */
            }
            
            .mobile-menu-modal .modal-content {
                padding-top: 60px; /* Уменьшен паддинг */
            }
            
            .floating-avatar-info, .user-balance {
                max-width: 230px;
            }
            
            .menu-grid {
                gap: 10px;
                max-width: 380px;
                height: 380px;
                margin-top: 15px;
            }
            .menu-item {
                padding: 10px 7px;
            }
            .menu-item i {
                font-size: 38px !important;
                margin-bottom: 6px;
            }
            .menu-item span {
                font-size: 0.7rem;
            }
            
            .user-info-container {
                margin-top: 15px;
            }
        }
        
        @media (max-width: 576px) {
            .floating-avatar-container {
                top: -35px; /* Уменьшен отступ */
            }
            
            .mobile-menu-modal .modal-content {
                padding-top: 50px; /* Уменьшен паддинг */
            }
            
            .floating-avatar-info, .user-balance {
                max-width: 220px;
            }
            
            .menu-grid {
                gap: 8px;
                max-width: 340px;
                height: 340px;
                margin-top: 10px;
            }
            .menu-item i {
                font-size: 36px !important;
            }
            .menu-item span {
                font-size: 0.65rem;
            }
            
            .user-info-container {
                margin-top: 12px;
            }
        }
        
        @media (max-width: 400px) {
            .floating-avatar {
                width: 90px;
                height: 90px;
            }
            
            .floating-avatar-container {
                top: -30px; /* Уменьшен отступ */
            }
            
            .mobile-menu-modal .modal-content {
                padding-top: 45px; /* Уменьшен паддинг */
            }
            
            .floating-avatar-info, .user-balance {
                max-width: 200px;
            }
            
            .menu-grid {
                gap: 6px;
                max-width: 300px;
                height: 300px;
                margin-top: 5px;
            }
            .menu-item i {
                font-size: 34px !important;
            }
            .menu-item span {
                font-size: 0.6rem;
            }
            
            .user-info-container {
                margin-top: 10px;
            }
        }
        
        @media (max-width: 340px) {
            .floating-avatar {
                width: 80px;
                height: 80px;
            }
            
            .floating-avatar-container {
                top: -25px; /* Уменьшен отступ */
            }
            
            .mobile-menu-modal .modal-content {
                padding-top: 40px; /* Уменьшен паддинг */
            }
            
            .floating-avatar-info, .user-balance {
                max-width: 180px;
            }
            
            .menu-grid {
                gap: 5px;
                max-width: 280px;
                height: 280px;
                margin-top: 0;
            }
            .menu-item i {
                font-size: 32px !important;
            }
            .menu-item span {
                font-size: 0.55rem;
            }
            
            .user-info-container {
                margin-top: 8px;
            }
        }
        
        @media (min-width: 769px) and (max-width: 1024px) {
            .mobile-menu-modal {
                max-height: 60vh;
                height: auto;
            }
            .floating-avatar-container {
                top: -45px; /* Возвращено исходное значение */
            }
            .mobile-menu-modal .modal-content {
                padding-top: 60px; /* Возвращено исходное значение */
            }
            .floating-avatar {
                width: 110px;
                height: 110px;
            }
            .floating-avatar-info {
                font-size: 1.1rem;
            }
            .user-balance {
                font-size: 1rem;
            }
            .menu-grid {
                max-width: 420px;
                height: 420px;
                margin-top: 25px;
            }
            .menu-item i {
                font-size: 38px !important;
            }
            .menu-item span {
                font-size: 0.8rem;
            }
            
            .user-info-container {
                margin-top: 25px;
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
        
        #mobileLoginRegister:hover {
            color: #00c6ff;
            transform: translateY(-2px);
        }
        
        /* Блокировка прокрутки при открытом меню */
        body.mobile-menu-open {
            overflow: hidden;
            position: relative;
            height: 100%;
        }

        /* Фикс для анимации */
        .circuit-layer,
        .particle {
            animation-play-state: paused;
        }
        
        .mobile-menu-modal.open .circuit-layer,
        .mobile-menu-modal.open .particle {
            animation-play-state: running;
        }
    `;
    document.head.appendChild(style);

    // Глобальные функции навигации
    window.goToLogin = function() {
        closeAllMobileMenus();
        setTimeout(() => {
            window.location.href = "/login";
        }, 100);
    }

    window.goToDashboard = function() {
        closeAllMobileMenus();
        setTimeout(() => {
            window.location.href = "/user/dashboard";
        }, 100);
    }

    // Функция для генерации HTML пользователя с кешированием
    function generateUserHTML() {
        if (userHTMLCache) return userHTMLCache;
        
        const userData = window.currentUser || {};
        let html;
        
        if (userData.first_name && userData.last_name) {
            const formattedBalance = (userData.balance || 0).toFixed(2);
            const fullName = `${userData.first_name} ${userData.last_name}`;
            
            let avatarHTML;
            if (userData.avatar_url) {
                avatarHTML = `<img src="${userData.avatar_url}" alt="User Avatar" class="avatar-image">`;
            } else {
                const initials = `${userData.first_name.charAt(0)}${userData.last_name.charAt(0)}`;
                avatarHTML = `<div class="avatar-placeholder" style="background-color: ${userData.avatar_color || '#1a2138'}">${initials}</div>`;
            }
            
            html = `
                <div class="floating-avatar" onclick="window.goToDashboard()">
                    ${avatarHTML}
                </div>
                <div class="user-info-container">
                    <div class="floating-avatar-info" onclick="window.goToDashboard()">
                        ${fullName}
                    </div>
                    <div class="user-balance" onclick="window.goToDashboard()">
                        ბალანსი: ${formattedBalance}₾
                    </div>
                </div>
            `;
        } else {
            html = `
                <div class="floating-avatar" onclick="window.goToLogin()">
                    <div class="avatar-placeholder">KODI.GE</div>
                </div>
                <div class="user-info-container">
                    <div class="floating-avatar-info not-logged-in" onclick="window.goToLogin()">
                        ლოგინი|რეგისტრაცია
                    </div>
                </div>
            `;
        }
        
        userHTMLCache = html;
        return html;
    }

    // Создаем HTML структуру мобильного меню
    function createMobileMenuStructure() {
        // Удаляем старый контейнер если существует
        const oldContainer = getElement('mobile-menu-container');
        if (oldContainer) {
            oldContainer.remove();
            // Очищаем кеш связанных элементов
            delete cachedElements['mobile-menu-container'];
            delete cachedElements['mobileMenuModal'];
            delete cachedElements['appleSubmenuModal'];
            delete cachedElements['androidSubmenuModal'];
        }
        
        const mobileMenuContainer = document.createElement('div');
        mobileMenuContainer.id = 'mobile-menu-container';
        document.body.appendChild(mobileMenuContainer);
        cachedElements['mobile-menu-container'] = mobileMenuContainer;
        
        const isDashboard = window.location.pathname.includes('dashboard');
        const userHTML = generateUserHTML();

        if (isDashboard) {
            createDashboardMobileMenu(mobileMenuContainer, userHTML);
        } else {
            createMainMobileMenu(mobileMenuContainer, userHTML);
        }

        // Восстановление состояния меню
        const savedMenuState = sessionStorage.getItem('mobileMenuState');
        if (savedMenuState) {
            sessionStorage.removeItem('mobileMenuState');
            setTimeout(() => {
                openMenuByState(savedMenuState);
            }, 50);
        }
    }

    function openMenuByState(state) {
        switch(state) {
            case 'main':
                if (getElement('mobileMenuModal')) {
                    openMobileMenu();
                }
                break;
            case 'apple':
                if (getElement('appleSubmenuModal')) {
                    openAppleSubmenu();
                }
                break;
            case 'android':
                if (getElement('androidSubmenuModal')) {
                    openAndroidSubmenu();
                }
                break;
        }
    }

    function createDashboardMobileMenu(container, userHTML) {
        container.innerHTML = `
            <div class="mobile-menu-modal" id="mobileMenuModal">
                <div class="modal-content">
                    <div class="tech-background">
                        <div class="circuit-layer"></div>
                        <div class="particle p1"></div>
                        <div class="particle p2"></div>
                        <div class="grid-matrix"></div>
                    </div>
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
                            <div class="menu-item" onclick="sessionStorage.setItem('mobileMenuState', 'main'); window.location.href='/';">
                                <i class="fas fa-home"></i>
                                <span>მთავარი</span>
                            </div>
                            <div class="menu-item" onclick="sessionStorage.setItem('mobileMenuState', 'main'); window.location.href='/user/accounts';">
                                <i class="fas fa-wallet"></i>
                                <span>ანგარიშები</span>
                            </div>
                            <div class="menu-item" onclick="sessionStorage.setItem('mobileMenuState', 'main'); window.location.href='/user/history_checks';">
                                <i class="fas fa-history"></i>
                                <span>IMEI ისტორია</span>
                            </div>
                            <div class="menu-item" onclick="sessionStorage.setItem('mobileMenuState', 'main'); window.location.href='/user/settings';">
                                <i class="fas fa-cog"></i>
                                <span>პარამეტრები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/auth/logout';">
                                <i class="fas fa-sign-out-alt"></i>
                                <span>გასვლა</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function createMainMobileMenu(container, userHTML) {
        container.innerHTML = `
            <!-- Mobile Menu Modal -->
            <div class="mobile-menu-modal" id="mobileMenuModal">
                <div class="modal-content">
                    <div class="tech-background">
                        <div class="circuit-layer"></div>
                        <div class="particle p1"></div>
                        <div class="particle p2"></div>
                        <div class="grid-matrix"></div>
                    </div>
                    <button class="close-modal" onclick="closeMobileMenu()">
                        <i class="fas fa-times"></i>
                    </button>
                    
                    <div class="floating-avatar-container">
                        ${userHTML}
                    </div>
                    
                    <div class="modal-body">
                        <div class="menu-grid">
                            <a class="menu-item" href="/" onclick="sessionStorage.setItem('mobileMenuState', 'main');">
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
                            <a class="menu-item" href="/compare" onclick="sessionStorage.setItem('mobileMenuState', 'main');">
                                <i class="fas fa-exchange-alt"></i>
                                <span>შედარება</span>
                            </a>
                            <a class="menu-item" href="/knowledge-base" onclick="sessionStorage.setItem('mobileMenuState', 'main');">
                                <i class="fas fa-book"></i>
                                <span>ცოდნის ბაზა</span>
                            </a>
                            <a class="menu-item" href="/contacts" onclick="sessionStorage.setItem('mobileMenuState', 'main');">
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
                <div class="modal-content">
                    <div class="tech-background">
                        <div class="circuit-layer"></div>
                        <div class="particle p1"></div>
                        <div class="particle p2"></div>
                        <div class="grid-matrix"></div>
                    </div>
                    <button class="close-modal" onclick="closeAppleSubmenu()">
                        <i class="fas fa-times"></i>
                    </button>

                    <div class="floating-avatar-container">
                        ${userHTML}
                    </div>
                    
                    <div class="modal-body">
                        <div class="menu-grid">
                            <a class="menu-item" href="/applecheck?type=free" onclick="sessionStorage.setItem('mobileMenuState', 'apple');">
                                <img src="static/ico/8f1197c9-19f4-4923-8030-4f7b88c9d697_20250627_012614_0000.png" 
                                     class="menu-icon-img">
                                <span>უფასო შემოწმება</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=fmi" onclick="sessionStorage.setItem('mobileMenuState', 'apple');">
                                <img src="static/ico/f9a07c0e-e427-4a1a-aab9-948ba60f1b6a_20250627_012716_0000.png" 
                                     class="menu-icon-img">
                                <span>FMI iCloud</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=sim_lock" onclick="sessionStorage.setItem('mobileMenuState', 'apple');">
                                <img src="static/ico/957afe67-7a27-48cb-9622-6c557b220b71_20250627_012808_0000.png" 
                                     class="menu-icon-img">
                                <span>SIM ლოკი</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=blacklist" onclick="sessionStorage.setItem('mobileMenuState', 'apple');">
                                <img src="static/ico/4e28c4f2-541b-4a1b-8163-c79e6db5481c_20250627_012852_0000.png" 
                                     class="menu-icon-img">
                                <span>შავი სია</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=mdm" onclick="sessionStorage.setItem('mobileMenuState', 'apple');">
                                <img src="static/ico/275e6a62-c55e-48b9-8781-5b323ebcdce0_20250627_012946_0000.png" 
                                     class="menu-icon-img">
                                <span>MDM ბლოკი</span>
                            </a>
                            <a class="menu-item" href="/applecheck?type=premium" onclick="sessionStorage.setItem('mobileMenuState', 'apple');">
                                <img src="static/ico/84df4824-0564-447c-b5c4-e749442bdc19_20250627_013110_0000.png" 
                                     class="menu-icon-img">
                                <span>პრემიუმ შემოწმება</span>
                            </a>
                            <a class="menu-item" href="#" onclick="alert('სერვისი მომზადების პროცესშია');">
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
                <div class="modal-content">
                    <div class="tech-background">
                        <div class="circuit-layer"></div>
                        <div class="particle p1"></div>
                        <div class="particle p2"></div>
                        <div class="grid-matrix"></div>
                    </div>
                    <button class="close-modal" onclick="closeAndroidSubmenu()">
                        <i class="fas fa-times"></i>
                    </button>

                    <div class="floating-avatar-container">
                        ${userHTML}
                    </div>
                    
                    <div class="modal-body">
                        <div class="menu-grid">
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
                                <i class="fab fa-samsung"></i>
                                <span>Samsung</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
                                <i class="fas fa-bolt"></i>
                                <span>Xiaomi</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
                                <i class="fab fa-google"></i>
                                <span>Pixel</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
                                <i class="fab fa-huawei"></i>
                                <span>Huawei</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
                                <i class="fas fa-circle"></i>
                                <span>Oppo</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
                                <i class="fab fa-android"></i>
                                <span>LG</span>
                            </a>
                            <a class="menu-item" href="/androidcheck" onclick="sessionStorage.setItem('mobileMenuState', 'android');">
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
    }

    // Mobile menu functions
    window.openMobileMenu = function() {
        const modal = getElement('mobileMenuModal');
        if (modal) {
            document.body.classList.add('mobile-menu-open');
            modal.style.display = 'flex';
            setTimeout(() => {
                modal.classList.add('open');
            }, 10);
        } else {
            // Если меню не найдено - пересоздаем
            createMobileMenuStructure();
            setTimeout(openMobileMenu, 50);
        }
    }

    window.closeMobileMenu = function() {
        const modal = getElement('mobileMenuModal');
        if (modal) {
            modal.classList.remove('open');
            setTimeout(() => {
                if (modal.classList.contains('open')) return;
                modal.style.display = 'none';
                document.body.classList.remove('mobile-menu-open');
            }, 400);
        }
    }

    window.openAppleSubmenu = function() {
        closeMobileMenu();
        setTimeout(() => {
            const appleModal = getElement('appleSubmenuModal');
            if (appleModal) {
                document.body.classList.add('mobile-menu-open');
                appleModal.style.display = 'flex';
                setTimeout(() => {
                    appleModal.classList.add('open');
                }, 10);
            } else {
                createMobileMenuStructure();
                setTimeout(openAppleSubmenu, 50);
            }
        }, 50);
    }

    window.closeAppleSubmenu = function() {
        const appleModal = getElement('appleSubmenuModal');
        if (appleModal) {
            appleModal.classList.remove('open');
            setTimeout(() => {
                if (appleModal.classList.contains('open')) return;
                appleModal.style.display = 'none';
                document.body.classList.remove('mobile-menu-open');
            }, 400);
        }
    }

    window.openAndroidSubmenu = function() {
        closeMobileMenu();
        setTimeout(() => {
            const androidModal = getElement('androidSubmenuModal');
            if (androidModal) {
                document.body.classList.add('mobile-menu-open');
                androidModal.style.display = 'flex';
                setTimeout(() => {
                    androidModal.classList.add('open');
                }, 10);
            } else {
                createMobileMenuStructure();
                setTimeout(openAndroidSubmenu, 50);
            }
        }, 50);
    }

    window.closeAndroidSubmenu = function() {
        const androidModal = getElement('androidSubmenuModal');
        if (androidModal) {
            androidModal.classList.remove('open');
            setTimeout(() => {
                if (androidModal.classList.contains('open')) return;
                androidModal.style.display = 'none';
                document.body.classList.remove('mobile-menu-open');
            }, 400);
        }
    }

    window.closeAllMobileMenus = function() {
        closeMobileMenu();
        closeAppleSubmenu();
        closeAndroidSubmenu();
        document.body.classList.remove('mobile-menu-open');
    }

    // Initialize mobile menu when the page loads
    document.addEventListener('DOMContentLoaded', () => {
        createMobileMenuStructure();
        
        // Mobile menu button setup
        const mobileMenuBtn = getElement('mobileMenuBtn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', function() {
                // Сбрасываем кеш пользовательских данных
                userHTMLCache = null;
                createMobileMenuStructure();
                setTimeout(openMobileMenu, 50);
            });
        }

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            const mobileMenuModal = getElement('mobileMenuModal');
            const appleSubmenuModal = getElement('appleSubmenuModal');
            const androidSubmenuModal = getElement('androidSubmenuModal');
            const floatingAvatar = document.querySelector('.floating-avatar-container');
            
            // Проверка для основного меню
            if (mobileMenuModal && mobileMenuModal.classList.contains('open') && 
                !mobileMenuModal.contains(e.target) && 
                e.target.id !== 'mobileMenuBtn' &&
                !(floatingAvatar && floatingAvatar.contains(e.target))) {
                closeMobileMenu();
            }
            
            // Проверка для подменю Apple
            if (appleSubmenuModal && appleSubmenuModal.classList.contains('open') && 
                !appleSubmenuModal.contains(e.target) && 
                e.target.id !== 'mobileMenuBtn' &&
                !(floatingAvatar && floatingAvatar.contains(e.target))) {
                closeAppleSubmenu();
            }
            
            // Проверка для подменю Android
            if (androidSubmenuModal && androidSubmenuModal.classList.contains('open') && 
                !androidSubmenuModal.contains(e.target) && 
                e.target.id !== 'mobileMenuBtn' &&
                !(floatingAvatar && floatingAvatar.contains(e.target))) {
                closeAndroidSubmenu();
            }
        });
    });
})();
