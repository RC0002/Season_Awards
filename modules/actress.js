// Actress Category Module
// Handles Best Actress specific functionality

export const ActressModule = {
    id: 'best-actress',
    title: 'Best Actress',
    placeholder: 'Actress name',
    searchType: 'person',
    isPerson: true,
    gender: 1, // Female

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
