// Film Category Module
// Handles Best Film specific functionality

export const FilmModule = {
    id: 'best-film',
    title: 'Best Film',
    placeholder: 'Film title',
    searchType: 'movie',
    isPerson: false,

    // Film-specific search configuration
    getSearchEndpoint() {
        return '/search/movie';
    },

    // Format search result for display
    formatResult(item) {
        return {
            name: item.title,
            year: item.release_date?.substring(0, 4) || '',
            imagePath: item.poster_path,
            tmdbId: item.id
        };
    },

    // Format entry for storage
    formatEntry(item) {
        return {
            name: item.title,
            posterPath: item.poster_path,
            tmdbId: item.id
        };
    }
};
