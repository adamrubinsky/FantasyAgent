// Backend configuration with real API fallback
// This provides both mock responses and real API integration

const REAL_API_ENDPOINT = 'https://YOUR_API_GATEWAY_ID.execute-api.us-east-1.amazonaws.com/prod';

class MockFantasyBackend {
    constructor() {
        this.isConnected = true;
        this.mockDelay = 800; // Simulate API response time
    }
    
    async mockApiCall(endpoint, data = {}) {
        // Try real API first, fallback to mock if it fails
        try {
            const response = await fetch(`${REAL_API_ENDPOINT}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: endpoint.replace('/api/', '').replace('-', '_'),
                    ...data
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Using real Lambda backend');
                return result;
            }
        } catch (error) {
            console.log('Real API failed, using mock backend:', error.message);
        }
        
        // Fallback to mock responses
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
        const message = (data.message || "").toLowerCase();
        
        // Provide context-aware responses based on the question
        let response = "";
        
        if (message.includes("after") && message.includes("qb")) {
            response = "After securing your QBs, target elite WRs like CeeDee Lamb, Tyreek Hill, or A.J. Brown. Then grab a top RB like Breece Hall, Bijan Robinson, or Jonathan Taylor. Don't forget a TE - Travis Kelce or Sam LaPorta are great picks.";
        } else if (message.includes("player") || message.includes("who should") || message.includes("pick")) {
            response = "Top targets right now:\n• QBs: Josh Allen, Lamar Jackson, Dak Prescott\n• RBs: Christian McCaffrey, Breece Hall, Bijan Robinson\n• WRs: CeeDee Lamb, Tyreek Hill, Justin Jefferson\n• TEs: Travis Kelce, Sam LaPorta, Mark Andrews";
        } else if (message.includes("rb") || message.includes("running back")) {
            response = "Best available RBs:\n1. Christian McCaffrey (SF)\n2. Breece Hall (NYJ)\n3. Bijan Robinson (ATL)\n4. Jonathan Taylor (IND)\n5. Saquon Barkley (PHI)\n6. Travis Etienne (JAX)";
        } else if (message.includes("wr") || message.includes("receiver")) {
            response = "Top WRs to target:\n1. CeeDee Lamb (DAL)\n2. Tyreek Hill (MIA)\n3. Justin Jefferson (MIN)\n4. A.J. Brown (PHI)\n5. Amon-Ra St. Brown (DET)\n6. Puka Nacua (LAR)";
        } else if (message.includes("compare")) {
            response = "Player comparison based on your question:\n• Josh Allen: Higher ceiling with rushing TDs, more consistent\n• Lamar Jackson: Elite rushing floor, week-winning upside\nIn SUPERFLEX, both are top-3 picks. Allen is safer, Lamar has higher ceiling.";
        } else if (message.includes("hello") || message.includes("hi")) {
            response = "Hey! I'm ready to help with your SUPERFLEX draft. What position do you need help with? Or tell me what pick you're at and I'll give you specific recommendations.";
        } else if (message.includes("roster") || message.includes("need")) {
            response = "For SUPERFLEX roster construction:\n• Rounds 1-2: Lock in 2 elite QBs\n• Rounds 3-5: Best available RB/WR\n• Round 6-7: TE if Kelce/Andrews available\n• Rounds 8+: Depth and upside plays";
        } else {
            // Default but still helpful response
            response = `For "${message}" - In SUPERFLEX, prioritize: \n1. Two starting QBs (rounds 1-4)\n2. 2-3 RBs (focus on workload)\n3. 3-4 WRs (target share matters)\n4. 1 elite TE\nNeed specific player recommendations? Just ask!`;
        }
        
        return {
            success: true,
            response: response,
            agent_type: "Fantasy AI Assistant",
            context_understood: true,
            message_processed: data.message
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