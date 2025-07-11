'use client'

import { useState, ComponentProps, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SOP_TEMPLATE } from '@/lib/sop-template'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'

// CodeBlock component for rendering code blocks with copy functionality
function CodeBlock({ children, ...props }: ComponentProps<'pre'>) {
  const [copied, setCopied] = useState(false)
  const preRef = useRef<HTMLPreElement>(null)
  
  const handleCopy = async () => {
    try {
      const textContent = preRef.current?.textContent
      if (textContent) {
        await navigator.clipboard.writeText(textContent)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    } catch (err) {
      console.error('Failed to copy text: ', err)
    }
  }
  
  return (
    <div className="relative group">
      <pre ref={preRef} className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 p-4 rounded-lg overflow-x-auto" {...props}>
        {children}
      </pre>
      <Button
        onClick={handleCopy}
        variant="outline"
        size="sm"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {copied ? '已复制!' : '复制'}
      </Button>
    </div>
  )
}

export default function Home() {
  // Existing states
  const [currentStep, setCurrentStep] = useState(1)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [generatedMarkdown, setGeneratedMarkdown] = useState('')
  
  // New states as specified
  const [idea, setIdea] = useState('')
  const [showWizard, setShowWizard] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  
  const currentStepData = SOP_TEMPLATE.find(item => item.step === currentStep)

  const handleNextStep = () => {
    setCurrentStep(currentStep + 1)
  }

  const handlePrevStep = () => {
    setCurrentStep(currentStep - 1)
  }

  const handleInputChange = (fieldId: string, value: string) => {
    setAnswers(prev => ({
      ...prev,
      [fieldId]: value
    }))
  }

  // New handler function as specified
  const handleAutoGenerate = async () => {
    if (!idea.trim()) return;
    
    setIsLoading(true);
    try {
      const response = await fetch('/api/auto-generate-plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ idea }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate plan');
      }
      
      const data = await response.json();
      
      if (data.success && data.plan) {
        setAnswers(data.plan);
        setShowWizard(true);
      }
    } catch (error) {
      console.error('Error generating plan:', error);
      alert('生成计划时出错，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateDocument = () => {
    let markdown = '# VibeDoc Development Plan\n\n'
    
    SOP_TEMPLATE.forEach(step => {
      markdown += `## ${step.title}\n\n`
      
      step.fields.forEach(field => {
        markdown += `### ${field.label}\n${answers[field.id] || 'N/A'}\n\n`
      })
    })
    
    // Generate AI coding prompts section
    markdown += '\n---\n\n'
    markdown += '# 🤖 AI 编程助手提示词\n\n'
    markdown += '以下是基于你的开发计划生成的分步骤AI编程提示词，你可以直接复制给编程AI使用：\n\n'
    
    // Task 1: Project Setup
    markdown += '## 任务 1: 项目初始化\n'
    markdown += '```\n'
    markdown += `请帮我创建一个新的项目：${answers.productName || '我的项目'}\n\n`
    markdown += `技术栈要求：${answers.techStack || 'Next.js + React + TypeScript'}\n\n`
    markdown += `项目描述：${answers.painPoints || '解决用户痛点的产品'}\n\n`
    markdown += `请设置好基础项目结构，包括必要的依赖和配置文件。\n`
    markdown += '```\n\n'
    
    // Task 2: Core Features
    markdown += '## 任务 2: 核心功能开发\n'
    markdown += '```\n'
    markdown += `请基于以下需求实现核心功能：\n\n`
    markdown += `主要功能点：${answers.newTerms || '核心功能特性'}\n\n`
    markdown += `技术实现：${answers.techStack || 'React组件 + API接口'}\n\n`
    markdown += `设计系统：${answers.designSystem || 'Tailwind CSS + 组件库'}\n\n`
    markdown += `请实现主要的用户界面和核心业务逻辑。\n`
    markdown += '```\n\n'
    
    // Task 3: API Development
    markdown += '## 任务 3: API 接口开发\n'
    markdown += '```\n'
    markdown += `请为项目创建必要的API接口：\n\n`
    markdown += `后端需求：${answers.developmentPlan || '用户管理、数据处理、业务逻辑'}\n\n`
    markdown += `数据处理：根据业务需求设计数据模型和API端点\n\n`
    markdown += `请实现RESTful API，包括数据验证和错误处理。\n`
    markdown += '```\n\n'
    
    // Task 4: UI/UX Implementation
    markdown += '## 任务 4: 界面设计实现\n'
    markdown += '```\n'
    markdown += `请实现响应式用户界面：\n\n`
    markdown += `设计系统：${answers.designSystem || 'Tailwind CSS + Shadcn/UI'}\n\n`
    markdown += `品牌理念：${answers.brandingConcept || '简洁、专业、易用'}\n\n`
    markdown += `目标用户：${answers.brandingConcept || '开发者和技术团队'}\n\n`
    markdown += `请创建美观、易用的用户界面，确保良好的用户体验。\n`
    markdown += '```\n\n'
    
    // Task 5: Deployment Setup
    markdown += '## 任务 5: 部署配置\n'
    markdown += '```\n'
    markdown += `请帮我配置项目部署：\n\n`
    markdown += `部署平台：${answers.hostingPlatform || 'Vercel'}\n\n`
    markdown += `域名配置：${answers.domainName || 'example.com'}\n\n`
    markdown += `SSL证书：${answers.sslCertificate || 'Let\'s Encrypt 自动配置'}\n\n`
    markdown += `性能优化：${answers.performanceOptimization || 'CDN、压缩、缓存'}\n\n`
    markdown += `请创建部署脚本和CI/CD配置。\n`
    markdown += '```\n\n'
    
    // Task 6: Analytics Integration
    markdown += '## 任务 6: 数据分析集成\n'
    markdown += '```\n'
    markdown += `请集成数据分析工具：\n\n`
    markdown += `分析平台：${answers.analyticsSetup || 'Google Analytics'}\n\n`
    markdown += `关键指标：${answers.kpiDefinition || '用户增长、留存率、转化率'}\n\n`
    markdown += `用户行为：${answers.userBehaviorAnalysis || '页面访问、功能使用、用户路径'}\n\n`
    markdown += `请实现数据埋点和分析报告功能。\n`
    markdown += '```\n\n'
    
    // Task 7: Testing & Optimization
    markdown += '## 任务 7: 测试与优化\n'
    markdown += '```\n'
    markdown += `请为项目添加测试和优化：\n\n`
    markdown += `测试策略：单元测试、集成测试、端到端测试\n\n`
    markdown += `性能监控：${answers.performanceMetrics || '页面加载速度、错误率、可用性'}\n\n`
    markdown += `用户反馈：${answers.userFeedback || '问卷调查、用户访谈、反馈收集'}\n\n`
    markdown += `请实现完整的测试套件和监控系统。\n`
    markdown += '```\n\n'
    
    // Task 8: Documentation
    markdown += '## 任务 8: 文档编写\n'
    markdown += '```\n'
    markdown += `请为项目创建完整文档：\n\n`
    markdown += `项目说明：${answers.productName || '产品名称'} - ${answers.painPoints || '解决的问题'}\n\n`
    markdown += `技术文档：API文档、部署指南、开发文档\n\n`
    markdown += `用户手册：功能介绍、使用教程、FAQ\n\n`
    markdown += `请创建README.md和完整的项目文档。\n`
    markdown += '```\n\n'
    
    markdown += '---\n\n'
    markdown += '💡 **使用提示：** 将上述每个任务的提示词复制给AI编程助手，它们会根据你的具体需求帮你完成开发工作。\n'
    
    setGeneratedMarkdown(markdown)
  }

  const handleStartOver = () => {
    setCurrentStep(1)
    setAnswers({})
    setGeneratedMarkdown('')
    setIdea('')
    setShowWizard(false)
  }

  // Initial AI input view - shown when showWizard is false
  if (!showWizard) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl font-bold text-center">
                VibeDoc AI 开发计划生成器
              </CardTitle>
              <p className="text-gray-600 text-center">
                输入你的想法，AI 将为你生成完整的开发计划
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="user-idea" className="text-sm font-medium">
                  你的产品想法
                  <span className="text-red-500 ml-1">*</span>
                </Label>
                <Textarea
                  id="user-idea"
                  placeholder="例如：我想做一个帮助开发者快速生成项目文档的AI工具..."
                  className="min-h-[120px]"
                  value={idea}
                  onChange={(e) => setIdea(e.target.value)}
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setShowWizard(true)}
              >
                手动填写
              </Button>
              <Button
                onClick={handleAutoGenerate}
                disabled={!idea.trim() || isLoading}
              >
                {isLoading ? '生成中...' : 'AI 生成计划'}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    )
  }

  if (!currentStepData) {
    return null
  }

  // Display generated document
  if (generatedMarkdown) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl font-bold">
                生成的开发计划
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose dark:prose-invert max-w-none p-6">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    pre: CodeBlock
                  }}
                >
                  {generatedMarkdown}
                </ReactMarkdown>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={handleStartOver} variant="outline">
                重新开始
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    )
  }

  // Wizard view - shown when showWizard is true
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl font-bold">
              步骤 {currentStepData.step}: {currentStepData.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {currentStepData.fields.map((field) => (
              <div key={field.id} className="space-y-2">
                <Label htmlFor={field.id} className="text-sm font-medium">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                {field.type === 'textarea' ? (
                  <Textarea
                    id={field.id}
                    placeholder={field.placeholder}
                    className="min-h-[120px]"
                    value={answers[field.id] || ''}
                    onChange={(e) => handleInputChange(field.id, e.target.value)}
                  />
                ) : (
                  <Input
                    id={field.id}
                    type="text"
                    placeholder={field.placeholder}
                    value={answers[field.id] || ''}
                    onChange={(e) => handleInputChange(field.id, e.target.value)}
                  />
                )}
              </div>
            ))}
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button
              variant="outline"
              onClick={() => setShowWizard(false)}
            >
              返回 AI 生成
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handlePrevStep}
                disabled={currentStep === 1}
              >
                上一步
              </Button>
              <Button
                onClick={currentStep === SOP_TEMPLATE.length ? handleGenerateDocument : handleNextStep}
                disabled={currentStep > SOP_TEMPLATE.length}
              >
                {currentStep === SOP_TEMPLATE.length ? '生成文档' : '下一步'}
              </Button>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}