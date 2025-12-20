// Director Category Module
// Handles Best Director specific functionality

export const DirectorModule = {
    id: 'best-director',
    title: 'Best Director',
    placeholder: 'Director name',
    searchType: 'person',
    isPerson: true,
    department: 'Directing',

    // Person-specific search configuration
    getSearchEndpoint() {
        return '/search/person';
    },

    // Format search result for display
    formatResult(item) {
        return {
            name: item.name,
            department: item.known_for_department || '',
            imagePath: item.profile_path,
            tmdbId: item.id
        };
    },

    // Format entry for storage
    formatEntry(item, filmTitle = '') {
        return {
            name: filmTitle ? `${item.name} — ${filmTitle}` : item.name,
            profilePath: item.profile_path,
            tmdbId: item.id
        };
    }
};
