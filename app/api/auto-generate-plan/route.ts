import { NextRequest, NextResponse } from 'next/server';
import { SOP_TEMPLATE } from '@/lib/sop-template';

export async function POST(request: NextRequest) {
  try {
    // Step 1: Read sop-template.ts and extract all field IDs
    const allFieldIds = SOP_TEMPLATE.flatMap(step => 
      step.fields.map(field => field.id)
    );

    // Step 2: Get User Input - Parse the incoming request's JSON body
    const body = await request.json();
    const { idea } = body;

    if (!idea) {
      return NextResponse.json(
        { error: 'Missing required field: idea' },
        { status: 400 }
      );
    }

    // Step 3: Get API Key from environment variables
    const apiKey = process.env.SILICONFLOW_API_KEY;
    
    if (!apiKey) {
      return NextResponse.json(
        { error: 'API key not configured' },
        { status: 500 }
      );
    }

    // Step 4: Construct Master Prompt with exact field IDs
    const masterPrompt = `You are an expert Product Manager and Technical Architect. Based on the user's idea, you must generate a comprehensive development plan.

CRITICAL REQUIREMENTS:
1. You MUST return ONLY a valid JSON object
2. The JSON object MUST have exactly these keys (field IDs): ${allFieldIds.join(', ')}
3. Each field must be filled with relevant, detailed content
4. Do not include any text before or after the JSON object
5. All values should be strings, not arrays or objects

Required JSON structure:
{
  "painPoints": "详细描述用户痛点和需要解决的问题",
  "newTerms": "相关的新兴概念、技术词汇或热门话题",
  "successCases": "参考的成功产品或案例，说明为什么值得学习",
  "productName": "产品名称",
  "domainName": "建议的域名",
  "brandingConcept": "品牌定位和核心概念",
  "techStack": "推荐的技术栈和开发工具",
  "deployment": "部署平台和方案",
  "developmentPlan": "详细的开发计划和时间安排",
  "designSystem": "UI/UX设计方案",
  "hostingPlatform": "托管和部署平台",
  "domainSetup": "域名配置和DNS设置",
  "sslCertificate": "HTTPS和SSL证书配置",
  "performanceOptimization": "性能优化策略",
  "socialMediaStrategy": "社交媒体推广计划",
  "productLaunch": "产品发布平台和策略",
  "contentMarketing": "内容营销计划",
  "communityBuilding": "用户社区和反馈渠道建设",
  "analyticsSetup": "网站分析和数据追踪工具配置",
  "kpiDefinition": "关键性能指标(KPI)定义",
  "userBehaviorAnalysis": "用户使用行为和路径分析",
  "performanceMetrics": "性能指标监控方案",
  "userFeedback": "用户反馈收集和处理机制",
  "productIteration": "产品功能迭代和优化计划",
  "marketingOptimization": "营销策略和推广效果优化",
  "businessModel": "商业模式和盈利方式优化"
}

User's idea: "${idea}"

Generate a complete development plan based on this idea. Return ONLY the JSON object with no additional text.`;

    // Step 5: Call Silicon Flow API with DeepSeek-V2 model
    const response = await fetch('https://api.siliconflow.cn/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'Qwen/Qwen2.5-72B-Instruct',
        messages: [
          {
            role: 'user',
            content: masterPrompt
          }
        ],
        temperature: 0.7,
        max_tokens: 4000
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Silicon Flow API error:', errorText);
      return NextResponse.json(
        { error: 'Failed to generate plan', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    
    // Step 6: Parse and Return - Extract content from response
    const generatedContent = data.choices?.[0]?.message?.content;
    
    if (!generatedContent) {
      return NextResponse.json(
        { error: 'No content generated from API' },
        { status: 500 }
      );
    }

    // Enhanced JSON parsing with better error handling
    let parsedPlan: Record<string, string>;
    try {
      // Clean the content - remove any potential markdown formatting
      const cleanContent = generatedContent
        .replace(/```json/g, '')
        .replace(/```/g, '')
        .trim();
      
      parsedPlan = JSON.parse(cleanContent) as Record<string, string>;
      
      // Validate that all required field IDs are present
      const missingFields = allFieldIds.filter(fieldId => !(fieldId in parsedPlan));
      if (missingFields.length > 0) {
        console.warn('Missing fields in AI response:', missingFields);
        // Fill missing fields with default values
        missingFields.forEach(fieldId => {
          parsedPlan[fieldId] = `请根据项目需求填写${fieldId}相关内容`;
        });
      }
      
    } catch (parseError) {
      console.error('JSON parsing error:', parseError);
      return NextResponse.json(
        { 
          error: 'Failed to parse AI response as JSON',
          details: parseError instanceof Error ? parseError.message : 'Unknown parse error',
          rawContent: generatedContent
        },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      plan: parsedPlan,
      originalIdea: idea,
      fieldIds: allFieldIds
    });

  } catch (error) {
    console.error('Error in auto-generate-plan API:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}