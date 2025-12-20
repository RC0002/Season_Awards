// Actor Category Module
// Handles Best Actor specific functionality

export const ActorModule = {
    id: 'best-actor',
    title: 'Best Actor',
    placeholder: 'Actor name',
    searchType: 'person',
    isPerson: true,
    gender: 2, // Male

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
