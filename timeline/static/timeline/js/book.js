/* Livre : pagination horizontale en colonnes, feuilletage, filtres */
(() => {
    const book = document.querySelector("[data-book]");
    if (!book) return;

    const clip = book.querySelector(".sv-book__clip");
    const flow = book.querySelector(".sv-book__flow");
    const paper = book.querySelector(".sv-book__paper");
    const prev = book.querySelector("[data-prev]");
    const next = book.querySelector("[data-next]");
    const counter = document.querySelector("[data-counter]");

    let current = 0;     // numéro de la double page affichée (ou de la page, sur téléphone)
    let total = 1;       // nombre de doubles pages
    let step = 0;        // largeur d'une double page + gouttière, en px
    let perView = 2;
    let columns = 1;

    function measure() {
        const style = getComputedStyle(flow);
        const gap = parseFloat(style.columnGap) || 0;
        perView = parseInt(style.columnCount, 10) || 1;
        const columnWidth = (clip.clientWidth - (perView - 1) * gap) / perView;
        step = clip.clientWidth + gap;
        columns = Math.max(1, Math.round((flow.scrollWidth + gap) / (columnWidth + gap)));
        total = Math.ceil(columns / perView);
    }

    function render() {
        flow.style.transform = `translateX(${-current * step}px)`;
        prev.disabled = current === 0;
        next.disabled = current >= total - 1;
        const first = current * perView + 1;
        const last = Math.min(columns, first + perView - 1);
        counter.textContent = perView === 1 || first === last ? `Page ${first} sur ${columns}` : `Pages ${first} et ${last} sur ${columns}`;
    }

    const DUREE_PAGE = 1100;
    const sansAnimation = window.matchMedia("(prefers-reduced-motion: reduce)");
    let flipping = false;

    // Double page sur laquelle se trouve chaque image du livre (-1 si elle n'est pas affichée)
    function imageSpreads() {
        const origin = flow.getBoundingClientRect().left;
        return [...flow.querySelectorAll("img")].map(picture => {
            const box = picture.getBoundingClientRect();
            return box.width ? Math.floor((box.left - origin + box.width / 2) / step) : -1;
        });
    }

    // Charge d'avance les photos des doubles pages voisines pour que le tour de page ne bute pas dessus
    function warm(spreads) {
        const where = imageSpreads();
        [...flow.querySelectorAll("img")].forEach((picture, i) => {
            if (spreads.includes(where[i])) picture.loading = "eager";
        });
    }

    // Copie figée du livre, réduite à une page : placée comme le vrai texte l'est dans la page, mais décalée de
    // `base` px vers la gauche. Rien de spécial pour le navigateur (pas de container query, pas de 3D à l'intérieur) :
    // la taille du texte et la hauteur des pages de garde sont recopiées en pixels.
    function ghostPage(spread, base, spreadOfImage) {
        const box = document.createElement("div");
        box.className = "sv-book__ghostbox";
        box.style.left = `${clip.offsetLeft - base}px`;
        box.style.top = `${clip.offsetTop}px`;
        box.style.width = `${clip.clientWidth}px`;
        box.style.height = `${clip.clientHeight}px`;

        const ghost = flow.cloneNode(true);
        ghost.classList.add("sv-book__flow--ghost");
        [...ghost.querySelectorAll("img")].forEach((picture, i) => {
            if (spreadOfImage[i] !== spread) { picture.removeAttribute("src"); picture.removeAttribute("srcset"); }
            picture.loading = "eager";
        });
        ghost.querySelectorAll("[data-lightbox], [data-open-group]").forEach(element => {
            element.removeAttribute("data-lightbox");
            element.removeAttribute("data-open-group");
        });
        ghost.querySelectorAll("a, button, input").forEach(control => { control.tabIndex = -1; });
        ghost.style.width = `${clip.clientWidth}px`;
        ghost.style.height = `${clip.clientHeight}px`;
        ghost.style.fontSize = getComputedStyle(flow).fontSize;
        ghost.style.setProperty("--sv-ghost-height", `${clip.clientHeight * 0.98}px`);
        ghost.style.transform = `translateX(${-spread * step}px)`;
        box.append(ghost);
        return box;
    }

    function sheet(element, width, offset) {
        element.style.backgroundSize = `${width * 2}px 100%`;
        element.style.backgroundPosition = `${-offset}px 0`;
    }

    // Vraie page qui se tourne, en 3D : un feuillet pleine page pivote autour de la reliure. Dessous, la page qui
    // reste est une copie de l'ancienne ; le vrai livre affiche déjà la nouvelle double page.
    function flip(target) {
        const forward = target > current;
        const from = current;
        flipping = true;
        warm([from, target]);
        const spreadOfImage = imageSpreads();
        const half = paper.clientWidth / 2;

        const stage = document.createElement("div");
        stage.className = "sv-book__stage";
        stage.setAttribute("aria-hidden", "true");

        const under = document.createElement("div");
        under.className = "sv-book__under";
        under.style.left = forward ? "0" : "50%";
        sheet(under, half, forward ? 0 : half);
        under.append(ghostPage(from, forward ? 0 : half, spreadOfImage));
        const underShade = document.createElement("div");
        underShade.className = "sv-book__shade sv-book__shade--under";
        under.append(underShade);

        const leaf = document.createElement("div");
        leaf.className = "sv-book__leaf";
        const front = document.createElement("div");
        front.className = "sv-book__face sv-book__face--front";
        sheet(front, half, half);
        front.append(ghostPage(forward ? from : target, half, spreadOfImage));
        const back = document.createElement("div");
        back.className = "sv-book__face sv-book__face--back";
        sheet(back, half, 0);
        back.append(ghostPage(forward ? target : from, 0, spreadOfImage));
        const frontShade = document.createElement("div");
        const backShade = document.createElement("div");
        frontShade.className = backShade.className = "sv-book__shade";
        front.append(frontShade);
        back.append(backShade);
        leaf.append(front, back);
        stage.append(under, leaf);
        book.append(stage);

        current = target;
        render();

        // Images clés déclarées d'avance : le navigateur déroule l'animation lui-même
        const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
        const STEPS = 40;
        const samples = [];
        for (let k = 0; k <= STEPS; k++) {
            const q = forward ? ease(k / STEPS) : 1 - ease(k / STEPS);     // 0 = feuillet à droite, 1 = à gauche
            const light = Math.sin(Math.PI * q);
            samples.push({ q, light });
        }
        const timing = { duration: DUREE_PAGE, easing: "linear", fill: "both" };
        const animations = [
            leaf.animate(samples.map(x => ({ transform: `rotateY(${-x.q * 180}deg) skewY(${(2.2 * x.light * (forward ? 1 : -1)).toFixed(2)}deg)` })), timing),
            frontShade.animate(samples.map(x => ({ opacity: 0.4 * Math.pow(x.light, 1.4) })), timing),
            backShade.animate(samples.map(x => ({ opacity: 0.4 * Math.pow(x.light, 1.4) })), timing),
            underShade.animate(samples.map(x => ({ opacity: 0.28 * x.light })), timing),
        ];

        let finished = false;
        const done = () => {
            if (finished) return;
            finished = true;
            stage.remove();
            book.classList.remove("sv-book--flipping");
            flipping = false;
            warm([current - 1, current + 1]);
        };
        book.classList.add("sv-book--flipping");
        Promise.all(animations.map(animation => animation.finished)).then(done, done);
        setTimeout(done, DUREE_PAGE + 700);     // filet de sécurité : jamais de feuillet resté en travers de la page
    }

    function go(target, animate = true) {
        target = Math.max(0, Math.min(total - 1, target));
        if (target === current || flipping) return;
        if (animate && perView === 2 && !sansAnimation.matches && leafSupported) {
            flip(target);
            return;
        }
        current = target;
        render();
    }

    const leafSupported = typeof Element.prototype.animate === "function";

    function refresh() {
        book.classList.add("sv-book--resizing");
        measure();
        current = Math.min(current, total - 1);
        render();
        requestAnimationFrame(() => book.classList.remove("sv-book--resizing"));
        warm([current - 1, current, current + 1]);
    }

    prev.addEventListener("click", () => go(current - 1));
    next.addEventListener("click", () => go(current + 1));

    document.addEventListener("keydown", event => {
        if (event.target.matches("input, select, textarea")) return;
        if (event.key === "ArrowRight") go(current + 1);
        else if (event.key === "ArrowLeft") go(current - 1);
    });

    // Molette ou pavé tactile : une page tournée par geste (pas sur téléphone, ni quand la visionneuse est ouverte)
    const telephone = window.matchMedia("(max-width: 48rem)");
    let lastWheel = 0;
    window.addEventListener("wheel", event => {
        if (telephone.matches || document.querySelector(".sv-lightbox:not([hidden])")) return;
        if (event.target.closest("select, input, textarea")) return;
        event.preventDefault();
        const now = performance.now();
        const newGesture = now - lastWheel > 180;
        lastWheel = now;
        const delta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
        if (newGesture && Math.abs(delta) >= 4) go(current + (delta > 0 ? 1 : -1));
    }, { passive: false });

    // Balayage au doigt ou à la souris
    let startX = null, startY = null;
    clip.addEventListener("pointerdown", event => { startX = event.clientX; startY = event.clientY; });
    window.addEventListener("pointerup", event => {
        if (startX === null) return;
        const dx = event.clientX - startX, dy = event.clientY - startY;
        startX = null;
        if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) go(current + (dx < 0 ? 1 : -1));
    });

    window.addEventListener("resize", refresh);
    window.addEventListener("load", refresh);
    if (document.fonts) document.fonts.ready.then(refresh);
    refresh();
})();
