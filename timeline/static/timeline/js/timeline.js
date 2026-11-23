/* Frise continue : toutes les années mises bout à bout, défilement fluide à la molette (verticale ou horizontale),
   au pavé tactile et au doigt ; le sélecteur d'année en cylindre suit le défilement ; miniatures chargées à l'approche */
(() => {
    const roll = document.querySelector("[data-roll]");
    const frise = document.querySelector("[data-frise]");
    if (!roll || !frise) return;

    const track = frise.querySelector(".sv-frise__track");
    const years = [...roll.querySelectorAll("[data-year]")];
    const yearInputs = document.querySelectorAll("[data-year-input]");
    const currentYear = new Date().getFullYear();
    const desktop = window.matchMedia("(min-width: 48.01rem)");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const RADIUS = 150;     // rayon du cylindre à taille normale, en px (il s'agrandit ou rétrécit avec la frise)
    const STEP = 27;        // degrés entre deux années voisines
    const VISIBLE = 3;      // années visibles de part et d'autre de celle du centre

    // ---------- Hauteur : la frise tient dans l'écran, sans défilement de la page ----------

    const timeline = frise.closest(".sv-timeline");
    const HEADER = 14.5;     // rem : en-tête (année, mois) et pied (titres du bas hors du fondu) de la frise à taille réelle
    const TIER = 8.8;           // rem : hauteur d'un étage de pastilles à taille réelle
    const MIN_SCALE = 0.12;
    const ROLL_HEIGHT = 24;     // rem : hauteur du cylindre à taille normale
    let rollScale = 1;
    let rollReady = false;

    function fit() {
        const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
        const style = getComputedStyle(track);
        const tiers = (parseInt(style.getPropertyValue("--sv-tiers-top"), 10) || 1) + (parseInt(style.getPropertyValue("--sv-tiers-bottom"), 10) || 1);
        // Début de la frise dans la page (sous le bandeau d'années sur téléphone ou en très fort zoom)
        const top = frise.getBoundingClientRect().top + window.scrollY;
        const below = parseFloat(getComputedStyle(document.querySelector(".sv-page")).paddingBottom) || 0;
        const available = window.innerHeight - top - below;
        const scale = Math.max(MIN_SCALE, Math.min(1, available / ((HEADER + tiers * TIER) * rem)));
        timeline.style.setProperty("--sv-avail", `${Math.floor(available)}px`);
        timeline.style.setProperty("--sv-k", scale.toFixed(3));
        if (desktop.matches) {
            rollScale = Math.max(0.35, Math.min(1.6, available / (ROLL_HEIGHT * rem)));
            timeline.style.setProperty("--sv-roll-s", rollScale.toFixed(3));
        } else {
            rollScale = 1;
            timeline.style.removeProperty("--sv-roll-s");
        }
        if (rollReady) drawRoll(position());
    }

    fit();
    window.addEventListener("resize", fit);
    document.querySelector(".sv-filters")?.addEventListener("toggle", fit);
    desktop.addEventListener("change", fit);
    if (document.fonts) document.fonts.ready.then(fit);

    // ---------- Géométrie : où commence chaque année, en px ----------

    let bounds = [];
    function measure() {
        const total = track.offsetWidth;
        bounds = years.map(button => ({
            start: Number(button.dataset.start) / 100 * total,
            width: Number(button.dataset.width) / 100 * total,
        }));
    }

    const maxScroll = () => Math.max(0, frise.scrollWidth - frise.clientWidth);
    const clamp = value => Math.max(0, Math.min(maxScroll(), value));

    // Position fractionnaire de l'année au centre de l'écran (0 = première année, 1 = la suivante, 0,5 = entre deux)
    function position() {
        const centre = frise.scrollLeft + frise.clientWidth / 2;
        let found = bounds.findIndex(b => centre < b.start + b.width);
        if (found < 0) found = bounds.length - 1;
        const b = bounds[found];
        return Math.max(0, Math.min(years.length - 1, found + (centre - b.start) / b.width - 0.5));
    }

    function todayScroll() {
        const index = years.findIndex(button => Number(button.dataset.year) === currentYear);
        if (index < 0) return null;
        const jours = (Date.UTC(currentYear + 1, 0, 1) - Date.UTC(currentYear, 0, 1)) / 86400000;
        const day = (Date.now() - Date.UTC(currentYear, 0, 1)) / 86400000;
        return bounds[index].start + bounds[index].width * day / jours - frise.clientWidth / 2;
    }

    function scrollForYear(index) {
        if (Number(years[index].dataset.year) === currentYear) return clamp(todayScroll());
        return clamp(bounds[index].start);
    }

    // ---------- Le cylindre ----------

    function drawRoll(at) {
        const selected = Math.round(at);
        years.forEach((button, i) => {
            const distance = i - at;
            const angle = Math.max(-75, Math.min(75, distance * STEP)) * Math.PI / 180;
            const hidden = desktop.matches && Math.abs(distance) > VISIBLE;
            button.style.setProperty("--sv-y", `${(RADIUS * rollScale * Math.sin(angle)).toFixed(1)}px`);
            button.style.setProperty("--sv-rx", `${(-angle * 180 / Math.PI).toFixed(1)}deg`);
            button.style.setProperty("--sv-s", Math.max(0.6, Math.cos(angle)).toFixed(2));
            button.style.setProperty("--sv-o", hidden ? 0 : Math.max(0, 1 - Math.abs(distance) * 0.28).toFixed(2));
            button.style.pointerEvents = hidden ? "none" : "";
            button.tabIndex = hidden ? -1 : 0;
            button.classList.toggle("is-selected", i === selected);
            button.toggleAttribute("aria-current", i === selected);
        });
        // Téléphone : le bandeau d'années garde l'année courante au centre
        if (!desktop.matches && selected !== shownOnMobile) {
            shownOnMobile = selected;
            const button = years[selected];
            roll.scrollTo({ left: button.offsetLeft - roll.clientWidth / 2 + button.clientWidth / 2, behavior: "smooth" });
        }
    }
    let shownOnMobile = -1;

    // ---------- Défilement : un peu de physique plutôt qu'un rattrapage de cible ----------
    //   - la molette donne de l'élan, qui s'éteint par frottement (plusieurs crans s'additionnent)
    //   - le pavé tactile suit directement le doigt (le système fournit déjà son inertie)
    //   - un clic sur une année déroule un trajet doux, du départ à l'arrivée
    //   - un glisser à la souris emporte la frise, qui continue sur sa lancée au lâcher

    const FRICTION = 330;     // ms : durée caractéristique de ralentissement
    const MAX_SPEED = 7;      // px/ms
    let pos = 0;              // position réelle (décimale) pendant un mouvement
    let velocity = 0;         // px/ms
    let mode = "idle";        // idle | inertia | tween
    let tween = null;
    let lastTime = 0;
    let ownScroll = false;

    const smooth = t => 0.5 - 0.5 * Math.cos(Math.PI * t);

    function write(value) {
        ownScroll = true;
        frise.scrollLeft = value;
    }

    function tick(now) {
        if (mode === "idle") return;
        const dt = lastTime ? Math.max(0, Math.min(48, now - lastTime)) : 16;
        lastTime = now;
        if (mode === "inertia") {
            pos += velocity * dt;
            velocity *= Math.exp(-dt / FRICTION);
            if (pos < 0 || pos > maxScroll()) { pos = clamp(pos); velocity = 0; }
            if (Math.abs(velocity) < 0.015) mode = "idle";
        } else {
            const t = Math.max(0, Math.min(1, (now - tween.start) / tween.duration));
            pos = tween.from + (tween.to - tween.from) * smooth(t);
            if (t >= 1) mode = "idle";
        }
        write(pos);
        if (mode !== "idle") requestAnimationFrame(tick);
    }

    function run() {
        lastTime = 0;
        requestAnimationFrame(tick);
    }

    function stop() {
        mode = "idle";
        velocity = 0;
    }

    function jumpTo(value) {
        stop();
        pos = clamp(value);
        write(pos);
    }

    // Trajet doux vers une position
    function scrollTo(value) {
        const to = clamp(value);
        if (reducedMotion.matches) return jumpTo(to);
        const wasIdle = mode === "idle";
        pos = frise.scrollLeft;
        velocity = 0;
        tween = { from: pos, to, start: performance.now(), duration: Math.min(1500, 650 + Math.abs(to - pos) / 5) };
        mode = "tween";
        if (wasIdle) run();
    }

    // Élan donné à la frise (px/ms)
    function fling(speed) {
        if (reducedMotion.matches) return;
        const wasIdle = mode === "idle";
        if (wasIdle || mode === "tween") pos = frise.scrollLeft;
        mode = "inertia";
        velocity = Math.max(-MAX_SPEED, Math.min(MAX_SPEED, speed));
        if (wasIdle) run();
    }

    // Déplacement direct, sans élan propre
    function nudge(delta) {
        stop();
        pos = clamp(frise.scrollLeft + delta);
        write(pos);
    }

    function goToYear(index) {
        index = Math.max(0, Math.min(years.length - 1, index));
        scrollTo(scrollForYear(index));
    }

    // Défilement natif (doigt, barre de défilement, clavier) : on repart de là où on est
    let urlTimer = 0;
    frise.addEventListener("scroll", () => {
        if (!ownScroll) { stop(); pos = frise.scrollLeft; }
        ownScroll = false;
        const at = position();
        drawRoll(at);
        clearTimeout(urlTimer);
        urlTimer = setTimeout(() => {
            const year = years[Math.round(at)].dataset.year;
            yearInputs.forEach(input => { input.value = year; });
            const url = new URL(window.location);
            url.searchParams.set("annee", year);
            history.replaceState(null, "", url);
        }, 250);
    }, { passive: true });

    // ---------- Molette : verticale ou horizontale, la frise défile ----------

    window.addEventListener("wheel", event => {
        if (!desktop.matches || event.ctrlKey) return;
        if (event.target.closest(".sv-filters, select, input, textarea, .sv-lightbox")) return;
        if (event.target.closest("[data-roll]")) return;
        const overFrise = event.target.closest("[data-frise]");
        const pageScrolls = document.documentElement.scrollHeight > window.innerHeight + 2;
        if (pageScrolls && !overFrise && Math.abs(event.deltaY) > Math.abs(event.deltaX)) return;
        const delta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
        if (!delta) return;
        event.preventDefault();
        const unit = event.deltaMode === 1 ? 32 : event.deltaMode === 2 ? frise.clientWidth : 1;
        const pixels = delta * unit;
        if (event.deltaMode === 0 && Math.abs(pixels) < 40) nudge(pixels * 1.25);      // pavé tactile : direct
        else fling((mode === "inertia" ? velocity : 0) + pixels * 0.0085);              // molette : de l'élan
    }, { passive: false });

    // Molette sur le cylindre : une année par cran
    let lastWheel = 0;
    roll.addEventListener("wheel", event => {
        event.preventDefault();
        if (Date.now() - lastWheel < 170) return;
        lastWheel = Date.now();
        goToYear(Math.round(position()) + Math.sign(event.deltaY));
    }, { passive: false });

    years.forEach((button, i) => button.addEventListener("click", () => {
        if (!roll.dataset.dragged) goToYear(i);
    }));

    roll.addEventListener("keydown", event => {
        const moves = { ArrowUp: -1, ArrowDown: 1, PageUp: -3, PageDown: 3 };
        const at = Math.round(position());
        if (event.key in moves) goToYear(at + moves[event.key]);
        else if (event.key === "Home") goToYear(0);
        else if (event.key === "End") goToYear(years.length - 1);
        else return;
        event.preventDefault();
    });

    frise.addEventListener("keydown", event => {
        const page = frise.clientWidth * 0.8;
        const moves = { ArrowLeft: -page / 2, ArrowRight: page / 2, PageUp: -page, PageDown: page };
        if (event.key in moves) scrollTo((mode === "tween" ? tween.to : frise.scrollLeft) + moves[event.key]);
        else if (event.key === "Home") scrollTo(0);
        else if (event.key === "End") scrollTo(maxScroll());
        else return;
        event.preventDefault();
    });

    // Glisser verticalement sur le cylindre (souris ou doigt)
    let startY = null;
    roll.addEventListener("pointerdown", event => { startY = event.clientY; delete roll.dataset.dragged; });
    window.addEventListener("pointermove", event => {
        if (startY === null || !desktop.matches) return;
        const delta = event.clientY - startY;
        if (Math.abs(delta) > 38) {
            goToYear(Math.round(position()) - Math.sign(delta));
            startY = event.clientY;
            roll.dataset.dragged = "1";
        }
    });
    window.addEventListener("pointerup", () => {
        startY = null;
        setTimeout(() => delete roll.dataset.dragged, 0);
    });

    // ---------- Cliquer-glisser à la souris, avec de l'élan au lâcher ----------

    let grab = null;       // { x, scroll, moved, samples }
    let wasDragged = false;

    frise.addEventListener("pointerdown", event => {
        if (event.pointerType !== "mouse" || event.button !== 0 || !desktop.matches) return;
        stop();
        grab = { x: event.clientX, scroll: frise.scrollLeft, moved: false, samples: [{ t: performance.now(), x: event.clientX }] };
    });

    window.addEventListener("pointermove", event => {
        if (!grab) return;
        const dx = event.clientX - grab.x;
        if (!grab.moved && Math.abs(dx) < 5) return;
        if (!grab.moved) {
            grab.moved = true;
            frise.classList.add("is-dragging");
        }
        pos = clamp(grab.scroll - dx);
        write(pos);
        const now = performance.now();
        grab.samples.push({ t: now, x: event.clientX });
        grab.samples = grab.samples.filter(sample => now - sample.t < 120);
    });

    window.addEventListener("pointerup", () => {
        if (!grab) return;
        const { moved, samples } = grab;
        grab = null;
        frise.classList.remove("is-dragging");
        if (!moved) return;
        wasDragged = true;
        setTimeout(() => { wasDragged = false; }, 0);
        const first = samples[0], last = samples[samples.length - 1];
        const speed = last.t > first.t ? (last.x - first.x) / (last.t - first.t) : 0;   // px par ms
        fling(-speed * 1.1);
    });

    // Un glisser ne doit pas ouvrir le moment sur lequel il a commencé, ni traîner l'image
    frise.addEventListener("click", event => {
        if (wasDragged) { event.preventDefault(); event.stopPropagation(); }
    }, true);
    frise.addEventListener("dragstart", event => event.preventDefault());

    // ---------- Détail des pastilles ----------

    // La carte s'ouvre à droite de la pastille, ou à gauche quand il n'y a plus la place
    frise.addEventListener("pointerover", event => {
        const pin = event.target.closest(".sv-pin");
        if (!pin) return;
        const room = frise.getBoundingClientRect().right - pin.getBoundingClientRect().right;
        pin.classList.toggle("sv-pin--flip", room < 17.5 * parseFloat(getComputedStyle(document.documentElement).fontSize) + 80);
    });

    // Sans survol (téléphone) : un premier toucher affiche le détail, le second ouvre le livre
    document.addEventListener("click", event => {
        const pin = event.target.closest(".sv-pin");
        document.querySelectorAll(".sv-pin.is-open").forEach(open => { if (open !== pin) open.classList.remove("is-open"); });
        if (pin && matchMedia("(hover: none)").matches && !pin.classList.contains("is-open")) {
            event.preventDefault();
            pin.classList.add("is-open");
        }
    });

    // ---------- Miniatures : chargées et décodées dès qu'on s'en approche (deux écrans de marge) ----------

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(entries => entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const picture = entry.target;
            picture.loading = "eager";
            if (picture.decode) picture.decode().catch(() => {});
            observer.unobserve(picture);
        }), { root: frise, rootMargin: "0px 200% 0px 200%" });
        frise.querySelectorAll(".sv-pin__cover img").forEach(picture => observer.observe(picture));
    }

    // ---------- Démarrage ----------

    function start() {
        measure();
        const wanted = years.findIndex(button => button.dataset.year === roll.dataset.selected);
        const index = wanted >= 0 ? wanted : years.findIndex(button => Number(button.dataset.year) === currentYear);
        jumpTo(scrollForYear(Math.max(0, index)));
        rollReady = true;
        drawRoll(position());
    }

    let resizeTimer = 0;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const at = position();
            measure();
            const index = Math.floor(at + 0.5);
            const b = bounds[Math.min(index, bounds.length - 1)];
            jumpTo(b.start + b.width * (at - index + 0.5) - frise.clientWidth / 2);
        }, 120);
    });

    start();
    window.addEventListener("load", start, { once: true });
    if (document.fonts) document.fonts.ready.then(() => { measure(); drawRoll(position()); });
})();
