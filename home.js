// ============ HOME PAGE MODULE ============
// Handles home page functionality: marquee animations, scatter effect

// Marquee state
let awardsPosition = 0;
let trendingPosition = 0;
let marqueeAnimationId = null;

// Initialize home page - called after data is loaded
async function initHomePage() {
    await populateAwardsMarquee();
    await populateTrendingMarquee();
    startMarqueeAnimations();
}

// Awards marquee - nominated films from all years
async function populateAwardsMarquee() {
    const marquee = document.getElementById('poster-marquee-awards');
    if (!marquee) return;

    marquee.innerHTML = '';
    const allPosters = [];

    // Collect posters from all categories in current data
    Object.values(data).forEach(categoryEntries => {
        categoryEntries.forEach(entry => {
            if (entry.posterPath && !allPosters.find(p => p.src.includes(entry.posterPath))) {
                allPosters.push({
                    src: `${CONFIG.TMDB_IMAGE_BASE}w342${entry.posterPath}`,
                    alt: entry.name
                });
            }
        });
    });

    // Fetch more posters from other years in Firebase
    if (firebaseReady && db) {
        try {
            const snapshot = await db.ref('awards').once('value');
            const allYearsData = snapshot.val();

            if (allYearsData) {
                Object.keys(allYearsData).forEach(year => {
                    const yearData = allYearsData[year];
                    if (yearData) {
                        Object.values(yearData).forEach(categoryEntries => {
                            if (Array.isArray(categoryEntries)) {
                                categoryEntries.forEach(entry => {
                                    if (entry.posterPath && !allPosters.find(p => p.src.includes(entry.posterPath))) {
                                        allPosters.push({
                                            src: `${CONFIG.TMDB_IMAGE_BASE}w342${entry.posterPath}`,
                                            alt: entry.name
                                        });
                                    }
                                });
                            }
                        });
                    }
                });
            }
        } catch (err) {
            console.warn('Could not fetch all years for marquee:', err);
        }
    }

    allPosters.sort(() => Math.random() - 0.5);
    const displayPosters = [...allPosters, ...allPosters, ...allPosters]; // Triple for seamless loop

    displayPosters.forEach(poster => {
        const img = document.createElement('img');
        img.src = poster.src;
        img.alt = poster.alt;
        img.loading = 'lazy';
        marquee.appendChild(img);
    });

    console.log(`🎬 Awards: ${allPosters.length} posters`);
}

// Trending marquee - popular movies from TMDB
async function populateTrendingMarquee() {
    const marquee = document.getElementById('poster-marquee-trending');
    if (!marquee) return;

    marquee.innerHTML = '';
    const trendingPosters = [];

    try {
        const url = `${CONFIG.TMDB_BASE_URL}/movie/popular?api_key=${CONFIG.TMDB_API_KEY}&language=en-US&page=1`;
        const res = await fetch(url);
        const json = await res.json();

        if (json.results) {
            json.results.forEach(movie => {
                if (movie.poster_path) {
                    trendingPosters.push({
                        src: `${CONFIG.TMDB_IMAGE_BASE}w342${movie.poster_path}`,
                        alt: movie.title
                    });
                }
            });
        }
    } catch (err) {
        console.warn('Could not fetch trending movies:', err);
    }

    const displayPosters = [...trendingPosters, ...trendingPosters, ...trendingPosters]; // Triple for seamless loop

    displayPosters.forEach(poster => {
        const img = document.createElement('img');
        img.src = poster.src;
        img.alt = poster.alt;
        img.loading = 'lazy';
        marquee.appendChild(img);
    });

    console.log(`🔥 Trending: ${trendingPosters.length} posters`);
}

// Smooth marquee animations using requestAnimationFrame
function startMarqueeAnimations() {
    const awardsMarquee = document.getElementById('poster-marquee-awards');
    const trendingMarquee = document.getElementById('poster-marquee-trending');

    if (marqueeAnimationId) {
        cancelAnimationFrame(marqueeAnimationId);
    }

    // Start positions - both start with full row visible
    awardsPosition = awardsMarquee ? -awardsMarquee.scrollWidth / 3 : 0;
    trendingPosition = trendingMarquee ? -trendingMarquee.scrollWidth / 3 : 0;

    function animate() {
        // Awards moves LEFT
        if (awardsMarquee && awardsMarquee.children.length) {
            awardsPosition -= 0.5;
            const thirdWidth = awardsMarquee.scrollWidth / 3;
            if (awardsPosition <= -thirdWidth) {
                awardsPosition = 0;
            }
            awardsMarquee.style.transform = `translateX(${awardsPosition}px)`;
        }

        // Trending moves RIGHT
        if (trendingMarquee && trendingMarquee.children.length) {
            trendingPosition += 0.5;
            const thirdWidth = trendingMarquee.scrollWidth / 3;
            if (trendingPosition >= 0) {
                trendingPosition = -thirdWidth;
            }
            trendingMarquee.style.transform = `translateX(${trendingPosition}px)`;
        }

        marqueeAnimationId = requestAnimationFrame(animate);
    }

    marqueeAnimationId = requestAnimationFrame(animate);
}

// Exit effect when leaving home page
// First carousel: all cards go UP
// Second carousel: all cards go DOWN
// Title: zooms in toward user
function scatterPosters() {
    // First carousel - all go UP
    const awardsPosters = document.querySelectorAll('.poster-marquee-awards img');
    awardsPosters.forEach(img => {
        const distance = 500 + Math.random() * 200;
        img.style.transition = 'transform 0.7s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.5s';
        img.style.transform = `translateY(-${distance}px)`;
        img.style.opacity = '0';
    });

    // Second carousel - all go DOWN
    const trendingPosters = document.querySelectorAll('.poster-marquee-trending img');
    trendingPosters.forEach(img => {
        const distance = 500 + Math.random() * 200;
        img.style.transition = 'transform 0.7s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.5s';
        img.style.transform = `translateY(${distance}px)`;
        img.style.opacity = '0';
    });

    // Title: slide left with the swipe
    const title = document.querySelector('.home-title');
    if (title) {
        title.style.transition = 'transform 0.6s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.4s';
        title.style.transform = 'translate(-150vw, -50%)';
        title.style.opacity = '0';
    }
}

// Reset posters and title after scatter
function resetPosters() {
    const posters = document.querySelectorAll('.poster-marquee img');
    posters.forEach(img => {
        img.style.transition = '';
        img.style.transform = '';
        img.style.opacity = '';
    });

    const title = document.querySelector('.home-title');
    if (title) {
        title.style.transition = '';
        title.style.transform = 'translate(-50%, -50%)';
        title.style.opacity = '';
    }
}
