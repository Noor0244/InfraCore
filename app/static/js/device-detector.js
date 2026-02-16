/**
 * Device Detection & Auto-Optimization Script
 * Automatically detects device type and screen size
 * Applies appropriate CSS classes and configurations
 * 
 * Runs on page load and listens for resize/orientation changes
 */

class DeviceDetector {
  constructor() {
    this.screenWidth = window.innerWidth;
    this.screenHeight = window.innerHeight;
    this.deviceType = this.detectDeviceType();
    this.orientation = this.getOrientation();
    this.dpi = window.devicePixelRatio || 1;
    
    this.init();
  }

  /**
   * Initialize device detection
   */
  init() {
    // Apply initial detection
    this.applyOptimizations();
    
    // Listen for window resize
    window.addEventListener('resize', () => this.handleResize());
    
    // Listen for orientation change
    window.addEventListener('orientationchange', () => this.handleOrientationChange());
    
    // Apply on load
    document.addEventListener('DOMContentLoaded', () => this.applyOptimizations());
  }

  /**
   * Detect device type based on screen width
   */
  detectDeviceType() {
    const width = this.screenWidth;
    
    if (width < 380) return 'small-phone';      // < 380px (older small phones)
    if (width < 480) return 'phone';            // 380-480px (standard phones)
    if (width < 768) return 'large-phone';      // 480-768px (phablets/large phones)
    if (width < 1024) return 'tablet';          // 768-1024px (tablets)
    if (width < 1280) return 'medium-screen';   // 1024-1280px (smaller laptops)
    return 'large-screen';                      // 1280px+ (desktop/large monitors)
  }

  /**
   * Get device orientation
   */
  getOrientation() {
    if (window.matchMedia('(orientation: landscape)').matches) {
      return 'landscape';
    }
    return 'portrait';
  }

  /**
   * Handle window resize
   */
  handleResize() {
    const newWidth = window.innerWidth;
    const newHeight = window.innerHeight;
    
    // Only update if significant change (> 50px)
    if (Math.abs(newWidth - this.screenWidth) > 50 || 
        Math.abs(newHeight - this.screenHeight) > 50) {
      this.screenWidth = newWidth;
      this.screenHeight = newHeight;
      this.deviceType = this.detectDeviceType();
      this.applyOptimizations();
      this.triggerRenderOptimization();
    }
  }

  /**
   * Handle orientation change
   */
  handleOrientationChange() {
    this.orientation = this.getOrientation();
    this.screenWidth = window.innerWidth;
    this.screenHeight = window.innerHeight;
    this.deviceType = this.detectDeviceType();
    this.applyOptimizations();
    this.triggerRenderOptimization();
  }

  /**
   * Apply all optimizations based on device type
   */
  applyOptimizations() {
    // Remove all device classes
    document.documentElement.classList.remove(
      'small-phone', 'phone', 'large-phone', 'tablet', 
      'medium-screen', 'large-screen'
    );
    
    // Remove all orientation classes
    document.documentElement.classList.remove('portrait', 'landscape');
    
    // Add current device class
    document.documentElement.classList.add(this.deviceType);
    document.documentElement.classList.add(this.orientation);
    
    // Apply custom data attributes
    document.documentElement.dataset.device = this.deviceType;
    document.documentElement.dataset.orientation = this.orientation;
    document.documentElement.dataset.screenWidth = Math.round(this.screenWidth);
    document.documentElement.dataset.screenHeight = Math.round(this.screenHeight);
    document.documentElement.dataset.dpi = this.dpi;
    
    // Apply device-specific optimizations
    this.optimizeForDevice();
    
    // Log for debugging
    console.log(`📱 Device Optimized: ${this.deviceType} (${this.screenWidth}x${this.screenHeight}px) - ${this.orientation}`);
  }

  /**
   * Optimize specific elements based on device type
   */
  optimizeForDevice() {
    // Optimize forms for small screens
    if (this.screenWidth < 480) {
      this.optimizeForSmallPhone();
    }
    
    // Optimize for tablets
    if (this.deviceType.includes('tablet')) {
      this.optimizeForTablet();
    }
    
    // Hide unnecessary elements on small phones
    if (this.screenWidth < 380) {
      this.optimizeForVerySmallPhone();
    }

    // Desktop optimizations
    if (this.screenWidth >= 1024) {
      this.optimizeForDesktop();
    }
  }

  /**
   * Optimize forms for small phones
   */
  optimizeForSmallPhone() {
    document.documentElement.style.setProperty('--form-column-count', '1');
    document.documentElement.style.setProperty('--button-width', '100%');
    document.documentElement.style.setProperty('--input-height', '44px');
    document.documentElement.style.setProperty('--font-size-base', '14px');
    document.documentElement.style.setProperty('--padding-base', '12px');
    document.documentElement.style.setProperty('--gap-base', '8px');
  }

  /**
   * Optimize for very small phones (< 380px)
   */
  optimizeForVerySmallPhone() {
    document.documentElement.style.setProperty('--font-size-base', '12px');
    document.documentElement.style.setProperty('--padding-base', '8px');
    document.documentElement.style.setProperty('--gap-base', '4px');
    
    // Hide certain sections
    const decorativeElements = document.querySelectorAll(
      '.sidebar-icon, .page-header-subtitle, .help-text'
    );
    decorativeElements.forEach(el => {
      if (!el.closest('.critical-form-section')) {
        el.style.display = 'none';
      }
    });
  }

  /**
   * Optimize for tablets
   */
  optimizeForTablet() {
    document.documentElement.style.setProperty('--form-column-count', '2');
    document.documentElement.style.setProperty('--button-width', 'auto');
    document.documentElement.style.setProperty('--input-height', '40px');
    document.documentElement.style.setProperty('--font-size-base', '15px');
    document.documentElement.style.setProperty('--padding-base', '16px');
    document.documentElement.style.setProperty('--gap-base', '12px');
  }

  /**
   * Optimize for desktop
   */
  optimizeForDesktop() {
    document.documentElement.style.setProperty('--form-column-count', 'auto-fit');
    document.documentElement.style.setProperty('--button-width', 'auto');
    document.documentElement.style.setProperty('--input-height', '38px');
    document.documentElement.style.setProperty('--font-size-base', '16px');
    document.documentElement.style.setProperty('--padding-base', '20px');
    document.documentElement.style.setProperty('--gap-base', '16px');
  }

  /**
   * Trigger render optimization (lazy rendering, virtual scrolling, etc.)
   */
  triggerRenderOptimization() {
    // Remove style from hidden elements to improve rendering
    const hiddenElements = document.querySelectorAll('[style*="display: none"]');
    hiddenElements.forEach(el => {
      if (el.offsetParent === null) {
        el.style.willChange = 'auto';
      }
    });

    // Force reflow optimization for smooth transitions
    requestAnimationFrame(() => {
      document.body.style.willChange = 'auto';
    });
  }

  /**
   * Get device info (for debugging)
   */
  getDeviceInfo() {
    return {
      device: this.deviceType,
      orientation: this.orientation,
      width: this.screenWidth,
      height: this.screenHeight,
      dpi: this.dpi,
      userAgent: navigator.userAgent,
      available: {
        memory: navigator.deviceMemory ? `${navigator.deviceMemory}GB` : 'unknown',
        cores: navigator.hardwareConcurrency || 'unknown',
        connection: navigator.connection?.effectiveType || 'unknown',
      }
    };
  }

  /**
   * Check if device is mobile
   */
  isMobile() {
    return this.screenWidth < 768;
  }

  /**
   * Check if device is tablet
   */
  isTablet() {
    return this.screenWidth >= 768 && this.screenWidth < 1024;
  }

  /**
   * Check if device is desktop
   */
  isDesktop() {
    return this.screenWidth >= 1024;
  }

  /**
   * Enable touch optimizations
   */
  enableTouchOptimizations() {
    const html = document.documentElement;
    
    // Add touch class
    if (this.isMobile() || this.isTablet()) {
      html.classList.add('touch-device');
      html.classList.remove('no-touch');
      
      // Increase touch target sizes
      document.documentElement.style.setProperty('--touch-target-size', '48px');
      
      // Smooth scrolling
      document.documentElement.style.scrollBehavior = 'smooth';
    }
  }

  /**
   * Log device detection for debugging
   */
  logDeviceInfo() {
    console.group('📱 Device Detection Info');
    console.table(this.getDeviceInfo());
    console.log(`Screen dimensions: ${this.screenWidth}x${this.screenHeight}`);
    console.log(`Device type: ${this.deviceType}`);
    console.log(`Orientation: ${this.orientation}`);
    console.log(`DPI: ${this.dpi}`);
    console.groupEnd();
  }
}

// Initialize on script load
const deviceDetector = new DeviceDetector();

// Make it globally accessible
window.deviceDetector = deviceDetector;

// Log device info to console
if (window.location.search.includes('debug')) {
  deviceDetector.logDeviceInfo();
}
