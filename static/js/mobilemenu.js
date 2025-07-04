// static/js/mobilemenu.js
(function() {
    // Добавляем стили в head документа
    const style = document.createElement('style');
    style.id = 'mobile-menu-styles';
    style.textContent = `
        /* Мобильное меню и аватар */
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
            background: rgba(18, 26, 43, 0.95);
            border: 3px solid rgba(0, 198, 255, 0.4);
            border-radius: 30px 30px 0 0;
            box-shadow: 0 0 15px rgba(0, 198, 255, 0.3);
            overflow: visible;
            position: relative;
            width: 100%;
            height: 100%;
        }
        
        .mobile-menu-modal .modal-body {
            flex: 1;
            overflow: hidden;
            padding-bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
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
            background: transparent;
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
        }
        
        .avatar-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            color: #ffffff;
            font-weight: bold;
            font-size: 1.5rem;
            text-align: center;
            padding: 10px;
            text-shadow: 0 0 12px rgba(0, 198, 255, 0.8);
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
        }
        
        /* Остальные стили остаются без изменений */
        /* ... */
    `;
    document.head.appendChild(style);

    // Генерация HTML для пользователя
    function generateUserHTML() {
        if (window.currentUser) {
            return `
                <div class="floating-avatar" style="background-color: ${window.currentUser.avatar_color};" onclick="goToDashboard()">
                    <div class="avatar-placeholder">
                        ${window.currentUser.first_name.charAt(0)}${window.currentUser.last_name.charAt(0)}
                    </div>
                </div>
                <div class="user-info-container">
                    <div class="floating-avatar-info" onclick="goToDashboard()">
                        ${window.currentUser.first_name} ${window.currentUser.last_name}
                    </div>
                    <div class="user-balance" onclick="goToDashboard()">
                        ბალანსი: ${window.currentUser.balance.toFixed(2)}₾
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="floating-avatar" onclick="goToLogin()">
                    <div class="avatar-placeholder">KODI.GE</div>
                </div>
                <div class="user-info-container">
                    <div class="floating-avatar-info" onclick="goToLogin()">
                        ლოგინი|რეგისტრაცია
                    </div>
                </div>
            `;
        }
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
                            <div class="menu-item" onclick="window.location.href='/accounts'; closeAllMobileMenus();">
                                <i class="fas fa-wallet"></i>
                                <span>ანგარიშები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/history-checks'; closeAllMobileMenus();">
                                <i class="fas fa-history"></i>
                                <span>IMEI ისტორია</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/history-comparisons'; closeAllMobileMenus();">
                                <i class="fas fa-exchange-alt"></i>
                                <span>შედარებები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/settings'; closeAllMobileMenus();">
                                <i class="fas fa-cog"></i>
                                <span>პარამეტრები</span>
                            </div>
                            <div class="menu-item" onclick="window.location.href='/logout'; closeAllMobileMenus();">
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

    // Redirect to login
    window.goToLogin = function() {
        closeAllMobileMenus();
        window.location.href = "/auth/login";
    }

    // Redirect to dashboard
    window.goToDashboard = function() {
        closeAllMobileMenus();
        window.location.href = "/user/dashboard";
    }

    // Initialize mobile menu when the page loads
    document.addEventListener('DOMContentLoaded', () => {
        // Получаем данные пользователя из глобальной переменной
        window.currentUser = window.currentUser || null;
        
        // Создаем HTML структуру меню
        createMobileMenuStructure();
        
        // Create mobile menu button if not exists
        if (!document.getElementById('mobileMenuBottom')) {
            const menuBtn = document.createElement('div');
            menuBtn.className = 'mobile-menu-bottom';
            menuBtn.id = 'mobileMenuBottom';
            menuBtn.innerHTML = `
                <button class="mobile-menu-btn" id="mobileMenuBtn">
                    <i class="fas fa-bars"></i>
                </button>
            `;
            document.body.appendChild(menuBtn);
        }
        
        // Mobile menu button setup
        try {
            const mobileMenuBtn = document.getElementById('mobileMenuBtn');
            if (mobileMenuBtn) {
                mobileMenuBtn.addEventListener('click', openMobileMenu);
            } else {
                console.warn('Mobile menu button not found');
            }
        } catch(e) {
            console.error('Mobile menu setup error:', e);
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
