(function() {
    // Кеширование DOM элементов
    let cachedElements = {};
    
    function getElement(id) {
        if (!cachedElements[id]) {
            cachedElements[id] = document.getElementById(id);
        }
        return cachedElements[id];
    }

    // Добавляем стили
    const style = document.createElement('style');
    style.id = 'kodi-mobile-menu-styles';
    style.textContent = `
        .html, body {
          margin: 0;
          padding: 0;
        }
          
        .kodi-menu-bottom {
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            z-index: 1050;
            padding-bottom: env(safe-area-inset-bottom, 5px);
        }
        
        @media (max-width: 1024px) {
            .kodi-menu-bottom {
                display: block;
            }
        }
        
        .kodi-menu-btn {
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
            margin: auto;
            transition: all 0.3s ease;
            margin-bottom: 0px;
        }
        
        .kodi-menu-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 0 25px rgba(0, 198, 255, 0.7);
        }
        
        .kodi-menu-modal {
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 65vh;
            max-height: none;
            z-index: 1100;
            align-items: flex-end;
            transform: translateY(100%);
            transition: transform 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
            opacity: 1;
            overflow: visible;
            padding-top: 0;
            border-radius: 30px 30px 0 0;
            box-sizing: border-box;
        }
        
        .kodi-menu-modal.open {
            transform: translateY(0);
            display: flex;
        }
        
        /* Unique Circuit Board Background */
        .kodi-circuit-board-bg {
            background: 
                linear-gradient(135deg, #0a0e17 0%, #121a33 100%);
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
            padding-bottom: env(safe-area-inset-bottom, 0);
        }

        /* Unique circuit lines pattern */
        .kodi-circuit-board-bg::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                /* Horizontal tracks */
                linear-gradient(0deg, 
                    transparent 24%, 
                    rgba(0, 230, 255, 0.15) 25%,
                    rgba(0, 230, 255, 0.15) 26%,
                    transparent 27%,
                    transparent 49%,
                    rgba(0, 230, 255, 0.15) 50%,
                    rgba(0, 230, 255, 0.15) 51%,
                    transparent 52%,
                    transparent 74%,
                    rgba(0, 230, 255, 0.15) 75%,
                    rgba(0, 230, 255, 0.15) 76%,
                    transparent 77%
                ),
                /* Vertical tracks */
                linear-gradient(90deg, 
                    transparent 19%, 
                    rgba(0, 230, 255, 0.15) 20%,
                    rgba(0, 230, 255, 0.15) 21%,
                    transparent 22%,
                    transparent 44%,
                    rgba(0, 230, 255, 0.15) 45%,
                    rgba(0, 230, 255, 0.15) 46%,
                    transparent 47%,
                    transparent 69%,
                    rgba(0, 230, 255, 0.15) 70%,
                    rgba(0, 230, 255, 0.15) 71%,
                    transparent 72%,
                    transparent 94%,
                    rgba(0, 230, 255, 0.15) 95%,
                    rgba(0, 230, 255, 0.15) 96%,
                    transparent 97%
                );
            background-size: 100px 100px, 100px 100px;
            opacity: 0.7;
            z-index: 1;
        }
        
        .kodi-menu-modal .kodi-modal-body {
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
        
        /* Close button */
        .kodi-close-modal {
            position: absolute;
            top: 7px;
            right: 10px;
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
        
        .kodi-close-modal:hover {
            background: #ff5252;
            transform: scale(1.1);
            box-shadow: 0 0 15px rgba(255, 107, 107, 0.5);
        }
        
        /* Avatar positioning */
        .kodi-avatar-container {
            position: absolute;
            top: -60px;
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
        
        .kodi-floating-avatar,
        .kodi-user-info {
            pointer-events: auto;
        }
        
        .kodi-floating-avatar {
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
        
        .kodi-avatar-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 50%;
        }
        
        .kodi-avatar-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #0a0e17, #1a2138);
            color: #ffffff;
            font-weight: bold;
            font-size: 1.2rem;
            text-align: center;
            padding: 10px;
            text-shadow: 0 0 12px rgba(0, 198, 255, 0.8);
            border-radius: 50%;
        }
        
        .kodi-user-info-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            margin-bottom: 15px;
            margin-top: 20px;
        }
        
        .kodi-user-info {
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
        
        .kodi-user-info.not-logged-in {
            text-shadow: 0 0 5px #00c6ff, 0 0 10px #00c6ff;
            margin-top: 10px;
        }
        
        .kodi-user-balance {
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
        
        /* Menu icons */
        .kodi-menu-item i {
            font-size: 40px !important;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #00c6ff, #0072ff);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 0 8px rgba(0, 198, 255, 0.3);
        }
        
        .kodi-menu-icon-img {
            display: block;
            width: 40px !important;
            height: 40px !important;
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 7px;
            object-fit: contain;
            object-position: center;
        }
        
        /* Remove link decorations */
        .kodi-menu-item a,
        .kodi-user-info,
        .kodi-user-balance,
        .kodi-floating-avatar {
            text-decoration: none !important;
            outline: none !important;
        }
        
        /* Menu grid */
        .kodi-menu-grid {
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
            margin-top: 30px;
        }
        
        .kodi-menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 15px;
            background: linear-gradient(135deg, #1a2138cc, #0e1321cc);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(0, 198, 255, 0.6);
            aspect-ratio: 1 / 1;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 
                0 4px 12px rgba(0, 0, 0, 0.5),
                inset 0 0 10px rgba(0, 198, 255, 0.15);
            min-width: 0;
            min-height: 0;
            padding: 12px 8px;
            box-sizing: border-box;
            color: white;
            position: relative;
            z-index: 3;
        }
        
        .kodi-menu-item:hover {
            background: linear-gradient(135deg, #223056cc, #121a33cc);
            transform: translateY(-7px);
            border-color: var(--accent-color);
            box-shadow: 
                0 6px 16px rgba(0, 0, 0, 0.6),
                inset 0 0 15px rgba(0, 198, 255, 0.25);
        }
        
        .kodi-menu-item span {
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
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .kodi-menu-grid {
                gap: 10px;
                max-width: 380px;
                height: 380px;
                margin-top: 90px;
            }
            .kodi-menu-item {
                padding: 10px 7px;
            }
            .kodi-menu-item i {
                font-size: 38px !important;
                margin-bottom: 6px;
            }
            .kodi-menu-item span {
                font-size: 0.7rem;
            }
            
            .kodi-user-info-container {
                margin-top: 15px;
            }
        }
        
        @media (max-width: 576px) {
            .kodi-menu-grid {
                gap: 8px;
                max-width: 340px;
                height: 340px;
                margin-top: 80px;
            }
            .kodi-menu-item i {
                font-size: 36px !important;
            }
            .kodi-menu-item span {
                font-size: 0.65rem;
            }
        }
        
        @media (max-width: 400px) {
            .kodi-menu-grid {
                gap: 6px;
                max-width: 300px;
                height: 300px;
                margin-top: 70px;
            }
            .kodi-menu-item i {
                font-size: 34px !important;
            }
            .kodi-menu-item span {
                font-size: 0.6rem;
            }
        }
        
        @media (max-width: 340px) {
            .kodi-menu-grid {
                gap: 5px;
                max-width: 280px;
                height: 280px;
                margin-top: 60px;
            }
            .kodi-menu-item i {
                font-size: 32px !important;
            }
            .kodi-menu-item span {
                font-size: 0.55rem;
            }
        }
        
        @media (min-width: 769px) and (max-width: 1024px) {
            .kodi-menu-modal {
                max-height: 55vh;
                height: auto;
            }
            .kodi-avatar-container {
                top: -35px;
            }
            .kodi-floating-avatar {
                width: 110px;
                height: 110px;
            }
            .kodi-user-info {
                font-size: 1.1rem;
            }
            .kodi-user-balance {
                font-size: 1rem;
            }
            .kodi-menu-grid {
                max-width: 420px;
                height: 420px;
                margin-top: 90px;
            }
            .kodi-menu-item i {
                font-size: 38px !important;
            }
            .kodi-menu-item span {
                font-size: 0.8rem;
            }
        }
        
        /* Hide on desktop */
        @media (min-width: 1025px) {
            .kodi-menu-modal {
                display: none !important;
            }
            .kodi-menu-bottom {
                display: none !important;
            }
        }
        
        /* Block scroll when menu is open */
        body.kodi-menu-open {
            overflow: hidden;
            position: relative;
            height: 100%;
        }
    `;
    document.head.appendChild(style);

    // Navigation functions
    window.kodiGoToLogin = function() {
        kodiCloseAllMenus();
        setTimeout(() => {
            window.location.href = "/login";
        }, 100);
    }

    window.kodiGoToDashboard = function() {
        kodiCloseAllMenus();
        setTimeout(() => {
            window.location.href = "/user/dashboard";
        }, 100);
    }

    // Generate user HTML
    function generateUserHTML() {
        const userData = window.currentUser || {};
        let html;
        
        if (userData.first_name && userData.last_name) {
            const formattedBalance = (userData.balance || 0).toFixed(2);
            const fullName = `${userData.first_name} ${userData.last_name}`;
            
            let avatarHTML;
            if (userData.avatar_url) {
                avatarHTML = `<img src="${userData.avatar_url}" alt="User Avatar" class="kodi-avatar-image">`;
            } else {
                const initials = `${userData.first_name.charAt(0)}${userData.last_name.charAt(0)}`;
                avatarHTML = `<div class="kodi-avatar-placeholder" style="background-color: ${userData.avatar_color || '#1a2138'}">${initials}</div>`;
            }
            
            html = `
                <div class="kodi-floating-avatar" onclick="kodiGoToDashboard()">
                    ${avatarHTML}
                </div>
                <div class="kodi-user-info-container">
                    <div class="kodi-user-info" onclick="kodiGoToDashboard()">
                        ${fullName}
                    </div>
                    <div class="kodi-user-balance" onclick="kodiGoToDashboard()">
                        ბალანსი: ${formattedBalance}₾
                    </div>
                </div>
            `;
        } else {
            html = `
                <div class="kodi-floating-avatar" onclick="kodiGoToLogin()">
                    <div class="kodi-avatar-placeholder">KODI.GE</div>
                </div>
                <div class="kodi-user-info-container">
                    <div class="kodi-user-info not-logged-in" onclick="kodiGoToLogin()">
                        ლოგინი|რეგისტრაცია
                    </div>
                </div>
            `;
        }
        
        return html;
    }

    // Create mobile menu structure
    function createMobileMenuStructure() {
        // Remove old container if exists
        const oldContainer = getElement('kodi-menu-container');
        if (oldContainer) {
            oldContainer.remove();
            delete cachedElements['kodi-menu-container'];
            delete cachedElements['kodiMainMenu'];
            delete cachedElements['kodiAppleMenu'];
            delete cachedElements['kodiAndroidMenu'];
        }
        
        const mobileMenuContainer = document.createElement('div');
        mobileMenuContainer.id = 'kodi-menu-container';
        document.body.appendChild(mobileMenuContainer);
        cachedElements['kodi-menu-container'] = mobileMenuContainer;
        
        const isDashboard = window.location.pathname.includes('dashboard');
        const userHTML = generateUserHTML();

        if (isDashboard) {
            createDashboardMenu(mobileMenuContainer, userHTML);
        } else {
            createMainMenu(mobileMenuContainer, userHTML);
        }
    }

    function createDashboardMenu(container, userHTML) {
        container.innerHTML = `
            <div class="kodi-menu-modal" id="kodiMainMenu">
                <div class="kodi-circuit-board-bg">
                    <div class="modal-header">
                        <button class="kodi-close-modal" onclick="kodiCloseMenu()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="kodi-modal-body">
                        <div class="kodi-avatar-container">
                            ${userHTML}
                        </div>
                        <div class="kodi-menu-grid">
                            <div class="kodi-menu-item" onclick="window.location.href='/';">
                                <i class="fas fa-home"></i>
                                <span>მთავარი</span>
                            </div>
                            <div class="kodi-menu-item" onclick="window.location.href='/user/accounts';">
                                <i class="fas fa-wallet"></i>
                                <span>ანგარიშები</span>
                            </div>
                            <div class="kodi-menu-item" onclick="window.location.href='/user/history_checks';">
                                <i class="fas fa-history"></i>
                                <span>IMEI ისტორია</span>
                            </div>
                            <div class="kodi-menu-item" onclick="window.location.href='/user/settings';">
                                <i class="fas fa-cog"></i>
                                <span>პარამეტრები</span>
                            </div>
                            <div class="kodi-menu-item" onclick="window.location.href='/auth/logout';">
                                <i class="fas fa-sign-out-alt"></i>
                                <span>გასვლა</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function createMainMenu(container, userHTML) {
        container.innerHTML = `
            <!-- Main Menu -->
            <div class="kodi-menu-modal" id="kodiMainMenu">
                <button class="kodi-close-modal" onclick="kodiCloseMenu()">
                    <i class="fas fa-times"></i>
                </button>
                
                <div class="kodi-avatar-container">
                    ${userHTML}
                </div>
                
                <div class="kodi-circuit-board-bg">
                    <div class="kodi-modal-body">
                        <div class="kodi-menu-grid">
                            <a class="kodi-menu-item" href="/">
                                <i class="fas fa-home"></i>
                                <span>მთავარი</span>
                            </a>
                            <div class="kodi-menu-item" onclick="kodiOpenAppleMenu()">
                                <i class="fab fa-apple"></i>
                                <span>Apple</span>
                            </div>
                            <div class="kodi-menu-item" onclick="kodiOpenAndroidMenu()">
                                <i class="fab fa-android"></i>
                                <span>Android</span>
                            </div>
                            <div class="kodi-menu-item disabled">
                                <i class="fas fa-unlock-alt"></i>
                                <span>განბლოკვა</span>
                            </div>
                            <a class="kodi-menu-item" href="/compares">
                                <i class="fas fa-exchange-alt"></i>
                                <span>შედარება</span>
                            </a>
                            <a class="kodi-menu-item" href="/knowledge-base">
                                <i class="fas fa-book"></i>
                                <span>ცოდნის ბაზა</span>
                            </a>
                            <a class="kodi-menu-item" href="/contacts">
                                <i class="fas fa-address-card"></i>
                                <span>კონტაქტი</span>
                            </a>
                            <div class="kodi-menu-item">
                                <i class="fas fa-shield-alt"></i>
                                <span>კონფიდენციალურობა</span>
                            </div>
                            <div class="kodi-menu-item">
                                <i class="fas fa-undo"></i>
                                <span>დაბრუნება</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Apple Submenu -->
            <div class="kodi-menu-modal" id="kodiAppleMenu">
                <button class="kodi-close-modal" onclick="kodiCloseAppleMenu()">
                    <i class="fas fa-times"></i>
                </button>

                <div class="kodi-avatar-container">
                    ${userHTML}
                </div>
                
                <div class="kodi-circuit-board-bg">
                    <div class="kodi-modal-body">
                        <div class="kodi-menu-grid">
                            <a class="kodi-menu-item" href="/applecheck?type=free">
                                <img src="static/ico/8f1197c9-19f4-4923-8030-4f7b88c9d697_20250627_012614_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>უფასო შემოწმება</span>
                            </a>
                            <a class="kodi-menu-item" href="/applecheck?type=fmi">
                                <img src="static/ico/f9a07c0e-e427-4a1a-aab9-948ba60f1b6a_20250627_012716_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>FMI iCloud</span>
                            </a>
                            <a class="kodi-menu-item" href="/applecheck?type=sim_lock">
                                <img src="static/ico/957afe67-7a27-48cb-9622-6c557b220b71_20250627_012808_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>SIM ლოკი</span>
                            </a>
                            <a class="kodi-menu-item" href="/applecheck?type=blacklist">
                                <img src="static/ico/4e28c4f2-541b-4a1b-8163-c79e6db5481c_20250627_012852_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>შავი სია</span>
                            </a>
                            <a class="kodi-menu-item" href="/applecheck?type=mdm">
                                <img src="static/ico/275e6a62-c55e-48b9-8781-5b323ebcdce0_20250627_012946_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>MDM ბლოკი</span>
                            </a>
                            <a class="kodi-menu-item" href="/applecheck?type=premium">
                                <img src="static/ico/84df4824-0564-447c-b5c4-e749442bdc19_20250627_013110_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>პრემიუმ შემოწმება</span>
                            </a>
                            <a class="kodi-menu-item" href="#" onclick="alert('სერვისი მომზადების პროცესშია');">
                                <img src="static/ico/874fae5b-c0f5-42d8-9c37-679aa86360e6_20250627_013030_0000.png" 
                                     class="kodi-menu-icon-img">
                                <span>MacBook</span>
                            </a>
                            <div class="kodi-menu-item" onclick="kodiCloseAppleMenu()">
                                <i class="fas fa-arrow-left"></i>
                                <span>უკან</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Android Submenu -->
            <div class="kodi-menu-modal" id="kodiAndroidMenu">
                <button class="kodi-close-modal" onclick="kodiCloseAndroidMenu()">
                    <i class="fas fa-times"></i>
                </button>

                <div class="kodi-avatar-container">
                    ${userHTML}
                </div>
                
                <div class="kodi-circuit-board-bg">
                    <div class="kodi-modal-body">
                        <div class="kodi-menu-grid">
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fab fa-samsung"></i>
                                <span>Samsung</span>
                            </a>
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fas fa-bolt"></i>
                                <span>Xiaomi</span>
                            </a>
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fab fa-google"></i>
                                <span>Pixel</span>
                            </a>
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fab fa-huawei"></i>
                                <span>Huawei</span>
                            </a>
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fas fa-circle"></i>
                                <span>Oppo</span>
                            </a>
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fab fa-android"></i>
                                <span>LG</span>
                            </a>
                            <a class="kodi-menu-item" href="/androidcheck">
                                <i class="fas fa-ellipsis-h"></i>
                                <span>სხვა</span>
                            </a>
                            <div class="kodi-menu-item" onclick="kodiCloseAndroidMenu()">
                                <i class="fas fa-arrow-left"></i>
                                <span>უკან</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Menu functions
    window.kodiOpenMenu = function() {
        const modal = getElement('kodiMainMenu');
        if (modal) {
            document.body.classList.add('kodi-menu-open');
            modal.style.display = 'flex';
            setTimeout(() => {
                modal.classList.add('open');
            }, 10);
        } else {
            createMobileMenuStructure();
            setTimeout(kodiOpenMenu, 50);
        }
    }

    window.kodiCloseMenu = function() {
        const modal = getElement('kodiMainMenu');
        if (modal) {
            modal.classList.remove('open');
            setTimeout(() => {
                if (modal.classList.contains('open')) return;
                modal.style.display = 'none';
                document.body.classList.remove('kodi-menu-open');
            }, 400);
        }
    }

    window.kodiOpenAppleMenu = function() {
        kodiCloseMenu();
        setTimeout(() => {
            const appleModal = getElement('kodiAppleMenu');
            if (appleModal) {
                document.body.classList.add('kodi-menu-open');
                appleModal.style.display = 'flex';
                setTimeout(() => {
                    appleModal.classList.add('open');
                }, 10);
            } else {
                createMobileMenuStructure();
                setTimeout(kodiOpenAppleMenu, 50);
            }
        }, 50);
    }

    window.kodiCloseAppleMenu = function() {
        const appleModal = getElement('kodiAppleMenu');
        if (appleModal) {
            appleModal.classList.remove('open');
            setTimeout(() => {
                if (appleModal.classList.contains('open')) return;
                appleModal.style.display = 'none';
                document.body.classList.remove('kodi-menu-open');
            }, 400);
        }
    }

    window.kodiOpenAndroidMenu = function() {
        kodiCloseMenu();
        setTimeout(() => {
            const androidModal = getElement('kodiAndroidMenu');
            if (androidModal) {
                document.body.classList.add('kodi-menu-open');
                androidModal.style.display = 'flex';
                setTimeout(() => {
                    androidModal.classList.add('open');
                }, 10);
            } else {
                createMobileMenuStructure();
                setTimeout(kodiOpenAndroidMenu, 50);
            }
        }, 50);
    }

    window.kodiCloseAndroidMenu = function() {
        const androidModal = getElement('kodiAndroidMenu');
        if (androidModal) {
            androidModal.classList.remove('open');
            setTimeout(() => {
                if (androidModal.classList.contains('open')) return;
                androidModal.style.display = 'none';
                document.body.classList.remove('kodi-menu-open');
            }, 400);
        }
    }

    window.kodiCloseAllMenus = function() {
        kodiCloseMenu();
        kodiCloseAppleMenu();
        kodiCloseAndroidMenu();
        document.body.classList.remove('kodi-menu-open');
    }

    // Initialize menu
    document.addEventListener('DOMContentLoaded', () => {
        createMobileMenuStructure();
        
        // Menu button setup
        const menuBtn = getElement('kodiMenuBtn');
        if (menuBtn) {
            menuBtn.addEventListener('click', function() {
                createMobileMenuStructure();
                setTimeout(kodiOpenMenu, 50);
            });
        }

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            const mainMenu = getElement('kodiMainMenu');
            const appleMenu = getElement('kodiAppleMenu');
            const androidMenu = getElement('kodiAndroidMenu');
            const avatarContainer = document.querySelector('.kodi-avatar-container');
            
            // Main menu check
            if (mainMenu && mainMenu.classList.contains('open') && 
                !mainMenu.contains(e.target) && 
                e.target.id !== 'kodiMenuBtn' &&
                !(avatarContainer && avatarContainer.contains(e.target))) {
                kodiCloseMenu();
            }
            
            // Apple menu check
            if (appleMenu && appleMenu.classList.contains('open') && 
                !appleMenu.contains(e.target) && 
                e.target.id !== 'kodiMenuBtn' &&
                !(avatarContainer && avatarContainer.contains(e.target))) {
                kodiCloseAppleMenu();
            }
            
            // Android menu check
            if (androidMenu && androidMenu.classList.contains('open') && 
                !androidMenu.contains(e.target) && 
                e.target.id !== 'kodiMenuBtn' &&
                !(avatarContainer && avatarContainer.contains(e.target))) {
                kodiCloseAndroidMenu();
            }
        });
    });
})();
