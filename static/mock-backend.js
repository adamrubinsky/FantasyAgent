// Mock backend for immediate frontend interactivity
// This simulates the AgentCore backend responses

class MockFantasyBackend {
    constructor() {
        this.isConnected = true;
        this.mockDelay = 800; // Simulate API response time
    }
    
    async mockApiCall(endpoint, data = {}) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, this.mockDelay));
        
        switch(endpoint) {
            case '/api/draft-advice':
                return this.getMockDraftAdvice(data);
            case '/api/available-players':
                return this.getMockAvailablePlayers(data);
            case '/api/chat':
                return this.getMockChatResponse(data);
            case '/api/draft-status':
                return this.getMockDraftStatus(data);
            default:
                throw new Error(`Unknown endpoint: ${endpoint}`);
        }
    }
    
    getMockDraftAdvice(context) {
        const mockAdvice = [
            {
                player: "Josh Allen",
                position: "QB", 
                team: "BUF",
                reasoning: "SUPERFLEX format makes elite QBs premium. Allen's dual-threat ability and high floor make him the #1 pick.",
                confidence: 95,
                adp: 2.1,
                tier: 1
            },
            {
                player: "Lamar Jackson", 
                position: "QB",
                team: "BAL", 
                reasoning: "Another elite SUPERFLEX option. Rushing upside provides incredible ceiling in fantasy.",
                confidence: 90,
                adp: 3.2,
                tier: 1
            },
            {
                player: "Justin Jefferson",
                position: "WR",
                team: "MIN",
                reasoning: "Best WR in fantasy. Safe floor with massive ceiling. Consider if QBs are gone.",
                confidence: 88,
                adp: 1.1,
                tier: 1
            }
        ];
        
        return {
            success: true,
            recommendations: mockAdvice,
            round: context.round || 1,
            pick: context.pick || 1,
            league_format: "SUPERFLEX",
            timestamp: new Date().toISOString()
        };
    }
    
    getMockAvailablePlayers(filters = {}) {
        const mockPlayers = [
            {name: "Josh Allen", position: "QB", team: "BUF", rank: 1, adp: 2.1, tier: 1, status: "Healthy"},
            {name: "Lamar Jackson", position: "QB", team: "BAL", rank: 2, adp: 3.2, tier: 1, status: "Healthy"}, 
            {name: "Justin Jefferson", position: "WR", team: "MIN", rank: 3, adp: 1.1, tier: 1, status: "Healthy"},
            {name: "Christian McCaffrey", position: "RB", team: "SF", rank: 4, adp: 1.8, tier: 1, status: "Healthy"},
            {name: "Dak Prescott", position: "QB", team: "DAL", rank: 5, adp: 4.5, tier: 2, status: "Healthy"},
            {name: "Tyreek Hill", position: "WR", team: "MIA", rank: 6, adp: 5.2, tier: 1, status: "Healthy"},
            {name: "Travis Kelce", position: "TE", team: "KC", rank: 7, adp: 6.8, tier: 1, status: "Healthy"},
            {name: "Stefon Diggs", position: "WR", team: "HOU", rank: 8, adp: 7.1, tier: 2, status: "Healthy"},
            {name: "Saquon Barkley", position: "RB", team: "PHI", rank: 9, adp: 8.3, tier: 2, status: "Healthy"},
            {name: "Jalen Hurts", position: "QB", team: "PHI", rank: 10, adp: 9.1, tier: 2, status: "Healthy"}
        ];
        
        let filtered = mockPlayers;
        
        if (filters.position && filters.position !== 'ALL') {
            filtered = filtered.filter(p => p.position === filters.position);
        }
        
        return {
            success: true,
            players: filtered.slice(0, filters.limit || 50),
            total_available: filtered.length,
            position_filter: filters.position || 'ALL',
            superflex_note: "QBs ranked higher due to SUPERFLEX format"
        };
    }
    
    getMockChatResponse(data) {
        const message = data.message || "";
        const responses = [
            `In SUPERFLEX format, I'd prioritize Josh Allen or Lamar Jackson early. Their rushing ability gives them huge upside.`,
            `For your question about "${message}" - remember that QBs are more valuable in SUPERFLEX. Target 2 QBs in your first 4 picks.`,
            `Based on SUPERFLEX scoring, elite QBs can outscore RBs by 5-8 points per week. That's why Allen goes so early.`,
            `If you miss the top QBs, look for value in rounds 6-8. Guys like Geno Smith or Baker Mayfield can be solid QB2s.`,
            `SUPERFLEX strategy tip: Always have a backup plan. If your target QB gets taken, know your next 2-3 options.`
        ];
        
        return {
            success: true,
            response: responses[Math.floor(Math.random() * responses.length)],
            agent_type: "Fantasy AI Assistant (Mock Mode)",
            context_understood: true,
            message_processed: message
        };
    }
    
    getMockDraftStatus() {
        return {
            success: true,
            current_pick: 8,
            total_picks: 144,
            recent_picks: [
                {pick: 7, player: "Christian McCaffrey", position: "RB", team: "SF"},
                {pick: 6, player: "Justin Jefferson", position: "WR", team: "MIN"},
                {pick: 5, player: "Josh Allen", position: "QB", team: "BUF"},
                {pick: 4, player: "Lamar Jackson", position: "QB", team: "BAL"},
                {pick: 3, player: "Tyreek Hill", position: "WR", team: "MIA"}
            ],
            your_turn: false,
            time_remaining: null
        };
    }
}

// Make it globally available
window.mockBackend = new MockFantasyBackend();

// Override fetch for mock responses
const originalFetch = window.fetch;
window.useMockBackend = true; // Set this to false when real backend is ready

window.fetch = async function(url, options) {
    // If mock backend is enabled and this is an API call, use mock
    if (window.useMockBackend && url.includes('/api/')) {
        const endpoint = url.substring(url.indexOf('/api'));
        let data = {};
        
        if (options && options.body) {
            try {
                data = JSON.parse(options.body);
            } catch (e) {
                data = {};
            }
        }
        
        try {
            const response = await window.mockBackend.mockApiCall(endpoint, data);
            return new Response(JSON.stringify(response), {
                status: 200,
                headers: {'Content-Type': 'application/json'}
            });
        } catch (error) {
            return new Response(JSON.stringify({
                success: false,
                error: error.message
            }), {
                status: 500,
                headers: {'Content-Type': 'application/json'}
            });
        }
    }
    
    // Otherwise use original fetch
    return originalFetch.apply(this, arguments);
};