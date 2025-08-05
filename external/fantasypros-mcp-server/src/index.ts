#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

const API_KEY = process.env.FANTASYPROS_API_KEY;
if (!API_KEY) {
  throw new Error('FANTASYPROS_API_KEY environment variable is required');
}

class FantasyProsServer {
  private server: Server;
  private axiosInstance;

  constructor() {
    this.server = new Server(
      {
        name: 'fantasypros-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.axiosInstance = axios.create({
      baseURL: 'https://api.fantasypros.com/public/v2',
      headers: {
        'x-api-key': API_KEY,
      },
    });

    this.setupToolHandlers();
    
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'get_sport_news',
          description: 'Get news for a specific sport',
          inputSchema: {
            type: 'object',
            properties: {
              sport: {
                type: 'string',
                enum: ['nfl', 'mlb', 'nba', 'nhl'],
                description: 'Sport to get news for',
              },
              limit: {
                type: 'number',
                description: 'Number of news items to return (max 25)',
                minimum: 1,
                maximum: 25,
              },
              category: {
                type: 'string',
                enum: ['injury', 'recap', 'transaction', 'rumor', 'breaking'],
                description: 'Type of news to show',
              },
            },
            required: ['sport'],
          },
        },
        {
          name: 'get_players',
          description: 'Get player information for a specific sport',
          inputSchema: {
            type: 'object',
            properties: {
              sport: {
                type: 'string',
                enum: ['nfl', 'mlb', 'nba', 'nhl'],
                description: 'Sport to get players for',
              },
              playerId: {
                type: 'string',
                description: 'Filter by specific player ID',
              },
            },
            required: ['sport'],
          },
        },
        {
          name: 'get_rankings',
          description: 'Get consensus rankings for a sport',
          inputSchema: {
            type: 'object',
            properties: {
              sport: {
                type: 'string',
                enum: ['nfl', 'nba'],
                description: 'Sport to get rankings for',
              },
              position: {
                type: 'string',
                description: 'Position to filter by',
              },
              scoring: {
                type: 'string',
                enum: ['STD', 'PPR', 'HALF'],
                description: 'Scoring type (for NFL)',
              },
            },
            required: ['sport'],
          },
        },
        {
          name: 'get_projections',
          description: 'Get player projections for a sport',
          inputSchema: {
            type: 'object',
            properties: {
              sport: {
                type: 'string',
                enum: ['nfl', 'mlb', 'nba'],
                description: 'Sport to get projections for',
              },
              season: {
                type: 'string',
                description: 'Season year',
              },
              week: {
                type: 'string',
                description: 'Week number (for NFL)',
              },
              position: {
                type: 'string',
                description: 'Position to filter by',
              },
            },
            required: ['sport', 'season'],
          },
        },
        {
          name: 'get_all_news',
          description: 'Get all news from FantasyPros',
          inputSchema: {
            type: 'object',
            properties: {
              limit: {
                type: 'number',
                description: 'Number of news items to return (max 25)',
                minimum: 1,
                maximum: 25,
              },
              category: {
                type: 'string',
                enum: ['injury', 'recap', 'transaction', 'rumor', 'breaking'],
                description: 'Type of news items to show',
              },
            },
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        switch (request.params.name) {
          case 'get_sport_news':
            return await this.getNews(request.params.arguments);
          case 'get_players':
            return await this.getPlayers(request.params.arguments);
          case 'get_rankings':
            return await this.getRankings(request.params.arguments);
          case 'get_projections':
            return await this.getProjections(request.params.arguments);
          case 'get_all_news':
            return await this.getAllNews(request.params.arguments);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error) {
        if (axios.isAxiosError(error)) {
          return {
            content: [
              {
                type: 'text',
                text: `FantasyPros API error: ${
                  error.response?.data?.message || error.message
                }`,
              },
            ],
            isError: true,
          };
        }
        throw error;
      }
    });
  }

  private async getNews(args: any) {
    const { sport, limit = 25, category } = args;
    const params: any = { limit };
    if (category) params.category = category;

    const response = await this.axiosInstance.get(`/${sport}/news`, { params });
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  }

  private async getPlayers(args: any) {
    const { sport, playerId } = args;
    const params: any = {};
    if (playerId) params.player = playerId;

    const response = await this.axiosInstance.get(`/${sport}/players`, { params });
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  }

  private async getRankings(args: any) {
    const { sport, position = 'ALL', scoring = 'STD' } = args;
    const season = new Date().getFullYear().toString();
    const params: any = {
      position,
      scoring,
    };

    const response = await this.axiosInstance.get(
      `/${sport}/${season}/consensus-rankings`,
      { params }
    );
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  }

  private async getProjections(args: any) {
    const { sport, season, week, position } = args;
    const params: any = {};
    if (week) params.week = week;
    if (position) params.position = position;

    const response = await this.axiosInstance.get(
      `/${sport}/${season}/projections`,
      { params }
    );
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  }

  private async getAllNews(args: any) {
    const { limit = 25, category } = args;
    const params: any = { limit };
    if (category) params.category = category;

    const response = await this.axiosInstance.get('/json/all/news', { params });
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('FantasyPros MCP server running on stdio');
  }
}

const server = new FantasyProsServer();
server.run().catch(console.error);
