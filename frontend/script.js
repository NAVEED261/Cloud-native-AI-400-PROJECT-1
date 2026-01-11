// ================================================================
// CLOUD-NATIVE AI-400 | INTERACTIVE SCRIPT
// ================================================================

// Smooth scroll to section
function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// Mobile menu toggle
const menuToggle = document.querySelector('.menu-toggle');
const navbarMenu = document.querySelector('.navbar-menu');

if (menuToggle) {
    menuToggle.addEventListener('click', () => {
        navbarMenu.classList.toggle('active');
    });
}

// Update active nav link on scroll
window.addEventListener('scroll', () => {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
    });

    if (window.location.pathname === '/index.html' || window.location.pathname === '/' || window.location.pathname.includes('index.html')) {
        navLinks[0].classList.add('active');
    } else if (window.location.pathname.includes('project')) {
        navLinks[1].classList.add('active');
    } else if (window.location.pathname.includes('skills')) {
        navLinks[2].classList.add('active');
    } else if (window.location.pathname.includes('api')) {
        navLinks[3].classList.add('active');
    } else if (window.location.pathname.includes('github')) {
        navLinks[4].classList.add('active');
    }
});

// Add animation on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'slideInUp 0.8s ease forwards';
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe all cards on page load
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.feature-card, .tech-item, .stat-box');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.animationDelay = `${index * 0.1}s`;
        observer.observe(card);
    });
});

// Particle effect on click (optional fun effect)
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('btn')) {
        createParticles(e.clientX, e.clientY);
    }
});

function createParticles(x, y) {
    for (let i = 0; i < 5; i++) {
        const particle = document.createElement('div');
        particle.style.position = 'fixed';
        particle.style.left = x + 'px';
        particle.style.top = y + 'px';
        particle.style.pointerEvents = 'none';
        particle.style.width = '8px';
        particle.style.height = '8px';
        particle.style.borderRadius = '50%';
        particle.style.background = `hsl(${Math.random() * 360}, 100%, 50%)`;
        particle.style.boxShadow = '0 0 10px currentColor';
        document.body.appendChild(particle);

        const angle = (Math.PI * 2 * i) / 5;
        const velocity = 5;
        const vx = Math.cos(angle) * velocity;
        const vy = Math.sin(angle) * velocity;
        let life = 1;

        const animate = () => {
            life -= 0.02;
            x += vx;
            y += vy;

            particle.style.left = x + 'px';
            particle.style.top = y + 'px';
            particle.style.opacity = life;

            if (life > 0) {
                requestAnimationFrame(animate);
            } else {
                particle.remove();
            }
        };

        animate();
    }
}

console.log('✨ Cloud-Native AI-400 Frontend Loaded Successfully!');
