import express from 'express';
import cors from 'cors';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

const app = express();
const port = 3002;

app.use(cors());
app.use(express.json());

// MCP客户端缓存
const mcpClients = new Map();

/**
 * 创建MCP客户端连接
 */
async function createMCPClient(url, config = {}) {
  if (mcpClients.has(url)) {
    return mcpClients.get(url);
  }

  const client = new Client(
    {
      name: "vibedoc-agent",
      version: "1.0.0"
    },
    {
      capabilities: {
        tools: {}
      }
    }
  );

  const abortController = new AbortController();
  
  try {
    console.log(`🔗 连接到MCP服务: ${url}`);
    
    // 优先尝试StreamableHTTP传输
    try {
      const transport = new StreamableHTTPClientTransport(new URL(url), {
        headers: config.headers || {},
        signal: abortController.signal
      });
      
      await client.connect(transport);
      console.log(`✅ 使用StreamableHTTP连接成功: ${url}`);
      
    } catch (streamableHttpError) {
      console.log(`⚠️ StreamableHTTP连接失败，尝试SSE: ${streamableHttpError.message}`);
      
      // 回退到SSE传输 - 修复参数格式
      const transport = new SSEClientTransport(new URL(url), {
        headers: config.headers || {},
        signal: abortController.signal
      });
      
      await client.connect(transport);
      console.log(`✅ 使用SSE连接成功: ${url}`);
    }

    mcpClients.set(url, { client, abortController });
    return { client, abortController };
    
  } catch (error) {
    console.error(`❌ MCP连接失败: ${error.message}`);
    throw error;
  }
}

/**
 * 调用MCP工具
 */
app.post('/call-tool', async (req, res) => {
  try {
    const { url, toolName, arguments: toolArgs, config } = req.body;
    
    if (!url || !toolName) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: url, toolName'
      });
    }

    console.log(`🔧 调用MCP工具: ${toolName} at ${url}`);
    console.log(`📋 参数:`, JSON.stringify(toolArgs, null, 2));

    const { client } = await createMCPClient(url, config);
    
    const result = await client.callTool({
      name: toolName,
      arguments: toolArgs || {}
    });

    console.log(`✅ 工具调用成功: ${toolName}`);
    console.log(`📊 结果长度: ${JSON.stringify(result).length} 字符`);

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error(`❌ 工具调用失败: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
});

/**
 * 获取可用工具列表
 */
app.post('/list-tools', async (req, res) => {
  try {
    const { url, config } = req.body;
    
    if (!url) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameter: url'
      });
    }

    console.log(`📋 获取工具列表: ${url}`);

    const { client } = await createMCPClient(url, config);
    
    const tools = await client.listTools();

    console.log(`✅ 获取到 ${tools.tools.length} 个工具`);

    res.json({
      success: true,
      data: tools
    });

  } catch (error) {
    console.error(`❌ 获取工具列表失败: ${error.message}`);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * 健康检查
 */
app.get('/health', (req, res) => {
  res.json({
    success: true,
    message: 'MCP Bridge Service is running',
    timestamp: new Date().toISOString(),
    activeConnections: mcpClients.size
  });
});

/**
 * 关闭MCP连接
 */
app.post('/disconnect', (req, res) => {
  const { url } = req.body;
  
  if (url && mcpClients.has(url)) {
    const { abortController } = mcpClients.get(url);
    abortController.abort();
    mcpClients.delete(url);
    console.log(`🔌 断开MCP连接: ${url}`);
  } else {
    // 断开所有连接
    for (const [clientUrl, { abortController }] of mcpClients) {
      abortController.abort();
      console.log(`🔌 断开MCP连接: ${clientUrl}`);
    }
    mcpClients.clear();
  }
  
  res.json({
    success: true,
    message: url ? `Disconnected from ${url}` : 'Disconnected from all MCP services'
  });
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\n🛑 正在关闭MCP Bridge服务...');
  
  // 断开所有MCP连接
  for (const [url, { abortController }] of mcpClients) {
    abortController.abort();
    console.log(`🔌 断开MCP连接: ${url}`);
  }
  
  process.exit(0);
});

app.listen(port, () => {
  console.log(`🚀 MCP Bridge服务启动在端口 ${port}`);
  console.log(`📡 健康检查: http://localhost:${port}/health`);
  console.log(`🔧 工具调用: POST http://localhost:${port}/call-tool`);
  console.log(`📋 工具列表: POST http://localhost:${port}/list-tools`);
});
