// ===========================
// Initialize Mermaid
// ===========================
document.addEventListener("DOMContentLoaded", () => {
  // Initialize Mermaid diagrams
  mermaid.initialize({
    startOnLoad: true,
    theme: "dark",
    themeVariables: {
      primaryColor: "#3b82f6",
      primaryTextColor: "#fafafa",
      primaryBorderColor: "#60a5fa",
      lineColor: "#a1a1aa",
      arrowheadColor: "#a1a1aa",
      secondaryColor: "#1c1c1f",
      tertiaryColor: "#10b981",
      background: "#111113",
      mainBkg: "#3b82f6",
      secondBkg: "#1c1c1f",
      border1: "#3b82f6",
      border2: "#27272a",
      nodeBorder: "#60a5fa",
      clusterBkg: "#1c1c1f",
      clusterBorder: "rgba(255,255,255,0.06)",
      titleColor: "#fafafa",
      edgeLabelBackground: "#1c1c1f",
      actorTextColor: "#fafafa",
      actorBkg: "#27272a",
      actorBorder: "#60a5fa",
      actorLineColor: "#a1a1aa",
      signalColor: "#fafafa",
      signalTextColor: "#fafafa",
      labelBoxBkgColor: "#1c1c1f",
      labelBoxBorderColor: "#60a5fa",
      labelTextColor: "#fafafa",
      loopTextColor: "#fafafa",
      noteBkgColor: "#27272a",
      noteTextColor: "#fafafa",
      noteBorderColor: "#60a5fa",
      sectionBkgColor: "#1c1c1f",
      altSectionBkgColor: "#111113",
      sectionBkgColor2: "#27272a",
      taskBkgColor: "#3b82f6",
      taskTextColor: "#fafafa",
      taskTextLightColor: "#fafafa",
      activeTaskBkgColor: "#2563eb",
      activeTaskBorderColor: "#60a5fa",
      gridColor: "#27272a",
      doneTaskBkgColor: "#10b981",
      doneTaskBorderColor: "#059669",
      critBkgColor: "#ef4444",
      critBorderColor: "#dc2626",
      todayLineColor: "#f59e0b",
      textColor: "#fafafa",
    },
    flowchart: {
      curve: "basis",
      padding: 20,
      htmlLabels: true,
    },
  });

  // Mobile menu toggle
  initMobileMenu();

  // Smooth scrolling for navigation links
  initSmoothScrolling();

  // Demo tabs functionality
  initDemoTabs();

  // Subtle scroll reveal animations
  initScrollReveal();

  // Add active state to nav links on scroll
  initNavActiveState();

  // Copy code blocks on click
  initCodeCopyButtons();

  // Initialize scroll progress bar
  initScrollProgressBar();

  // Dynamic footer year
  initFooterYear();
});

// ===========================
// Mobile Menu
// ===========================
function initMobileMenu() {
  const hamburger = document.getElementById("hamburger");
  const navMenu = document.getElementById("navMenu");

  if (!hamburger || !navMenu) return;

  hamburger.addEventListener("click", () => {
    navMenu.classList.toggle("active");
    hamburger.classList.toggle("active");
  });

  // Close menu when clicking on a link
  const navLinks = navMenu.querySelectorAll(".nav-link");
  navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      navMenu.classList.remove("active");
      hamburger.classList.remove("active");
    });
  });

  // Close menu when clicking outside
  document.addEventListener("click", (e) => {
    if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
      navMenu.classList.remove("active");
      hamburger.classList.remove("active");
    }
  });
}

// ===========================
// Smooth Scrolling
// ===========================
function initSmoothScrolling() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const href = this.getAttribute("href");
      if (href === "#") return;

      e.preventDefault();
      const target = document.querySelector(href);

      if (target) {
        const navHeight = document.querySelector(".navbar").offsetHeight;
        const targetPosition =
          target.getBoundingClientRect().top + window.pageYOffset - navHeight;

        window.scrollTo({
          top: targetPosition,
          behavior: "smooth",
        });
      }
    });
  });
}

// ===========================
// Demo Tabs
// ===========================
function initDemoTabs() {
  const tabs = document.querySelectorAll(".demo-tab");
  const panels = document.querySelectorAll(".demo-panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetTab = tab.getAttribute("data-tab");

      // Remove active class from all tabs and panels
      tabs.forEach((t) => t.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));

      // Add active class to clicked tab and corresponding panel
      tab.classList.add("active");
      const targetPanel = document.getElementById(targetTab);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
    });
  });
}

// ===========================
// Scroll Reveal Animations
// ===========================
function initScrollReveal() {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  const revealElements = new Set();

  const revealGroups = [
    [".section-title", 0],
    [
      ".overview-card, .feature-card, .layer-card, .pattern-item, .doc-card, .community-card, .tech-category, .footer-section",
      30,
    ],
    [
      ".diagram-container, .architecture-description, .prerequisites, .example-usage, .workflow-table, .workflow-diagram, .custom-workflow, .contribution-steps, .acknowledgments, .demo-container, .footer-bottom",
      0,
    ],
    [
      ".stat-item, .step, .ui-feature, .demo-tab, .tools-list span, .workflow-table tbody tr",
      25,
    ],
    [
      ".feature-list li, .prerequisites li, .demo-panel li, .tech-category li, .contribution-steps li",
      15,
    ],
    [
      "section .container > *:not(.section-title), .cta-section .container > *",
      20,
    ],
  ];

  revealGroups.forEach(([selector, delayStep]) => {
    document.querySelectorAll(selector).forEach((element, index) => {
      if (element.classList.contains("reveal-on-scroll")) return;
      const delay = Math.min(index * delayStep, 150);
      element.classList.add("reveal-on-scroll");
      element.style.setProperty("--reveal-delay", `${delay}ms`);
      revealElements.add(element);
    });
  });

  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    revealElements.forEach((element) => element.classList.add("is-visible"));
    return;
  }

  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    {
      threshold: 0.14,
      rootMargin: "0px 0px -8% 0px",
    },
  );

  revealElements.forEach((element) => revealObserver.observe(element));
}

// ===========================
// Active Nav State on Scroll
// ===========================
function initNavActiveState() {
  const sections = document.querySelectorAll("section[id]");
  const navLinks = document.querySelectorAll(".nav-link");

  function updateActiveNav() {
    let current = "";
    const scrollPosition = window.pageYOffset;
    const navHeight = document.querySelector(".navbar").offsetHeight;

    // Find which section is currently in view
    sections.forEach((section) => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.clientHeight;

      // Check if section is in the viewport (with some offset for better UX)
      if (scrollPosition >= sectionTop - navHeight - 200) {
        current = section.getAttribute("id");
      }
    });

    // Update nav links
    navLinks.forEach((link) => {
      link.classList.remove("active");
      const href = link.getAttribute("href");

      if (href === `#${current}`) {
        link.classList.add("active");
      }
    });
  }

  // Update on scroll
  window.addEventListener("scroll", updateActiveNav);

  // Initial update on page load
  updateActiveNav();
}

// ===========================
// Code Copy Buttons
// ===========================
function initCodeCopyButtons() {
  const codeBlocks = document.querySelectorAll("pre code");

  codeBlocks.forEach((block) => {
    const pre = block.parentElement;
    if (!pre || pre.parentElement?.classList.contains("code-block-wrapper"))
      return;

    const wrapper = document.createElement("div");
    wrapper.className = "code-block-wrapper";

    // macOS window title bar with traffic lights
    const bar = document.createElement("div");
    bar.className = "code-window-bar";
    bar.innerHTML =
      '<span class="code-window-dot code-window-dot--close"></span>' +
      '<span class="code-window-dot code-window-dot--minimize"></span>' +
      '<span class="code-window-dot code-window-dot--maximize"></span>' +
      '<span class="code-window-title">' +
      detectLanguage(block.textContent) +
      "</span>";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code-btn";
    button.innerHTML =
      '<i class="fa-regular fa-copy" aria-hidden="true"></i> <span>Copy</span>';
    button.setAttribute("aria-label", "Copy code block");

    button.addEventListener("click", async () => {
      const code = block.textContent;
      try {
        await navigator.clipboard.writeText(code);
        button.classList.remove("failed");
        button.classList.add("copied");
        button.innerHTML =
          '<i class="fa-solid fa-check" aria-hidden="true"></i> <span>Copied</span>';

        setTimeout(() => {
          button.classList.remove("copied");
          button.innerHTML =
            '<i class="fa-regular fa-copy" aria-hidden="true"></i> <span>Copy</span>';
        }, 2000);
      } catch (err) {
        console.error("Failed to copy:", err);
        button.classList.remove("copied");
        button.classList.add("failed");
        button.innerHTML =
          '<i class="fa-solid fa-xmark" aria-hidden="true"></i> <span>Failed</span>';
        setTimeout(() => {
          button.classList.remove("failed");
          button.innerHTML =
            '<i class="fa-regular fa-copy" aria-hidden="true"></i> <span>Copy</span>';
        }, 2000);
      }
    });

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(bar);
    wrapper.appendChild(pre);
    wrapper.appendChild(button);
  });
}

function detectLanguage(text) {
  const trimmed = text.trim();
  if (
    trimmed.startsWith("$") ||
    trimmed.startsWith("#") ||
    trimmed.startsWith("./")
  )
    return "Terminal";
  if (trimmed.startsWith("git ")) return "Terminal";
  if (trimmed.startsWith("pip ") || trimmed.startsWith("ollama "))
    return "Terminal";
  if (/^(agents|workflows):/.test(trimmed)) return "agents.yaml";
  if (/^(orchestrator|Welcome to AI)/.test(trimmed)) return "Terminal";
  if (/import |from |def |class /.test(trimmed)) return "Python";
  if (/function |const |let |var |=>/.test(trimmed)) return "JavaScript";
  return "Code";
}

// ===========================
// Scroll Progress Bar
// ===========================
function initScrollProgressBar() {
  const progressBar = document.getElementById("progressBar");

  if (!progressBar) return;

  window.addEventListener("scroll", () => {
    const windowHeight =
      document.documentElement.scrollHeight -
      document.documentElement.clientHeight;
    const scrolled = (window.pageYOffset / windowHeight) * 100;
    progressBar.style.width = scrolled + "%";
  });
}

// ===========================
// Dynamic Footer Year
// ===========================
function initFooterYear() {
  const yearElement = document.getElementById("currentYear");
  if (!yearElement) return;
  yearElement.textContent = new Date().getFullYear().toString();
}

// ===========================
// Navbar Scroll Effect
// ===========================
let lastScroll = 0;
const navbar = document.querySelector(".navbar");

window.addEventListener("scroll", () => {
  const currentScroll = window.pageYOffset;

  // Add shadow on scroll
  if (currentScroll > 50) {
    navbar.style.boxShadow = "0 4px 20px rgba(0, 0, 0, 0.5)";
  } else {
    navbar.style.boxShadow = "none";
  }

  // Hide/show navbar on scroll (optional)
  // Uncomment to enable auto-hide on scroll down
  /*
    if (currentScroll > lastScroll && currentScroll > 100) {
        navbar.style.transform = 'translateY(-100%)';
    } else {
        navbar.style.transform = 'translateY(0)';
    }
    */

  lastScroll = currentScroll;
});

// ===========================
// Stats Counter Animation
// ===========================
function animateCounter(element, target, duration = 2000) {
  const start = 0;
  const increment = target / (duration / 16); // 60fps
  let current = start;

  const timer = setInterval(() => {
    current += increment;
    if (current >= target) {
      element.textContent = target;
      clearInterval(timer);
    } else {
      element.textContent = Math.floor(current);
    }
  }, 16);
}

// Observe stats and animate when visible
const statsObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (
        entry.isIntersecting &&
        !entry.target.classList.contains("animated")
      ) {
        entry.target.classList.add("animated");
        const number = entry.target.querySelector(".stat-number");
        if (number) {
          const targetText = number.textContent;
          const targetNumber = parseInt(targetText.replace(/\D/g, ""));
          if (!isNaN(targetNumber)) {
            number.textContent = "0";
            animateCounter(number, targetNumber);
          }
        }
      }
    });
  },
  { threshold: 0.5 },
);

document.querySelectorAll(".stat-item").forEach((stat) => {
  statsObserver.observe(stat);
});

// ===========================
// Easter Egg - Konami Code
// ===========================
let konamiCode = [];
const konamiSequence = [
  "ArrowUp",
  "ArrowUp",
  "ArrowDown",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowLeft",
  "ArrowRight",
  "b",
  "a",
];

document.addEventListener("keydown", (e) => {
  konamiCode.push(e.key);
  konamiCode = konamiCode.slice(-10);

  if (konamiCode.join("") === konamiSequence.join("")) {
    activateEasterEgg();
  }
});

function activateEasterEgg() {
  // Create confetti effect
  const colors = ["#3b82f6", "#60a5fa", "#2563eb", "#10b981", "#f59e0b"];
  const confettiCount = 100;

  for (let i = 0; i < confettiCount; i++) {
    setTimeout(() => {
      const confetti = document.createElement("div");
      confetti.style.cssText = `
                position: fixed;
                width: 10px;
                height: 10px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                top: -10px;
                left: ${Math.random() * 100}vw;
                border-radius: 50%;
                pointer-events: none;
                z-index: 9999;
                animation: fall ${2 + Math.random() * 3}s linear forwards;
            `;
      document.body.appendChild(confetti);

      setTimeout(() => confetti.remove(), 5000);
    }, i * 30);
  }

  // Add fall animation if not exists
  if (!document.getElementById("confetti-style")) {
    const style = document.createElement("style");
    style.id = "confetti-style";
    style.textContent = `
            @keyframes fall {
                to {
                    transform: translateY(100vh) rotate(${Math.random() * 360}deg);
                    opacity: 0;
                }
            }
        `;
    document.head.appendChild(style);
  }

  console.log("Easter egg activated! You found the secret.");
}

// ===========================
// Back to Top Button
// ===========================
function createBackToTopButton() {
  const button = document.createElement("button");
  button.id = "back-to-top";
  button.innerHTML = "↑";
  button.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 50px;
        height: 50px;
        background: #3b82f6;
        color: white;
        border: none;
        border-radius: 50%;
        font-size: 24px;
        cursor: pointer;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 999;
    `;

  button.addEventListener("click", () => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  });

  button.addEventListener("mouseover", () => {
    button.style.transform = "scale(1.1)";
  });

  button.addEventListener("mouseout", () => {
    button.style.transform = "scale(1)";
  });

  document.body.appendChild(button);

  // Show/hide button based on scroll
  window.addEventListener("scroll", () => {
    if (window.pageYOffset > 300) {
      button.style.opacity = "1";
      button.style.visibility = "visible";
    } else {
      button.style.opacity = "0";
      button.style.visibility = "hidden";
    }
  });
}

createBackToTopButton();

// ===========================
// Performance Optimization
// ===========================

// Lazy load fallback for browsers without native support
if (!("loading" in HTMLImageElement.prototype)) {
  // Fallback for browsers that don't support lazy loading
  const script = document.createElement("script");
  script.src =
    "https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js";
  document.body.appendChild(script);
}

// ===========================
// Console Easter Egg
// ===========================
console.log(
  "%cAI Orchestrator",
  "font-size: 24px; font-weight: bold; color: #3b82f6;",
);
console.log(
  "%cWelcome to the AI Coding Tools Orchestrator!",
  "font-size: 14px; color: #60a5fa;",
);
console.log(
  "%cInterested in contributing? Check out our GitHub repo!",
  "font-size: 12px; color: #10b981;",
);
console.log(
  "%cHint: Try the Konami Code",
  "font-size: 10px; color: #a1a1aa; font-style: italic;",
);

// ===========================
// Analytics (placeholder)
// ===========================
function trackEvent(category, action, label) {
  // Add your analytics tracking here
  // Example: Google Analytics, Plausible, etc.
  console.log("Event:", { category, action, label });
}

// Track button clicks
document.querySelectorAll(".btn").forEach((button) => {
  button.addEventListener("click", (e) => {
    const buttonText = button.textContent.trim();
    trackEvent("Button", "Click", buttonText);
  });
});

// Track navigation
document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", (e) => {
    const linkText = link.textContent.trim();
    trackEvent("Navigation", "Click", linkText);
  });
});

// ===========================
// Dark Mode Toggle (Optional)
// ===========================
function createDarkModeToggle() {
  // Uncomment to enable dark mode toggle
  /*
    const toggle = document.createElement('button');
    toggle.innerHTML = 'Moon';
    toggle.style.cssText = `
        position: fixed;
        top: 80px;
        right: 30px;
        width: 40px;
        height: 40px;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        font-size: 20px;
        cursor: pointer;
        z-index: 999;
        transition: all 0.3s ease;
    `;

    toggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        toggle.innerHTML = document.body.classList.contains('dark-mode') ? 'Sun' : 'Moon';
    });

    document.body.appendChild(toggle);
    */
}

// createDarkModeToggle();

// ===========================
// Initialize All Features
// ===========================
console.log("All features initialized successfully.");
