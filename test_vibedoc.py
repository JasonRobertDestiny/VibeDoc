#!/usr/bin/env python3
"""
VibeDoc 功能测试脚本
用于验证应用的核心功能是否正常工作
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入待测试的模块
try:
    from app_optimized import (
        validate_input,
        validate_url,
        format_response,
        extract_prompts_section,
        create_temp_markdown_file
    )
    print("✅ 成功导入优化版本模块")
except ImportError as e:
    print(f"❌ 导入优化版本失败: {e}")
    try:
        from app import generate_development_plan
        print("✅ 成功导入原版本模块")
    except ImportError as e:
        print(f"❌ 导入原版本失败: {e}")
        sys.exit(1)

class TestVibeDocFunctions(unittest.TestCase):
    """VibeDoc功能测试类"""

    def test_validate_input(self):
        """测试输入验证功能"""
        print("🧪 测试输入验证功能...")
        
        # 测试有效输入
        valid, msg = validate_input("这是一个有效的产品创意描述，包含足够的信息来生成开发计划")
        self.assertTrue(valid)
        self.assertEqual(msg, "")
        
        # 测试空输入
        valid, msg = validate_input("")
        self.assertFalse(valid)
        self.assertIn("请输入", msg)
        
        # 测试过短输入
        valid, msg = validate_input("太短")
        self.assertFalse(valid)
        self.assertIn("太短", msg)
        
        print("✅ 输入验证测试通过")

    def test_validate_url(self):
        """测试URL验证功能"""
        print("🧪 测试URL验证功能...")
        
        # 测试有效URL
        self.assertTrue(validate_url("https://www.example.com"))
        self.assertTrue(validate_url("http://deepwiki.org/some/path"))
        
        # 测试无效URL
        self.assertFalse(validate_url("not-a-url"))
        self.assertFalse(validate_url(""))
        self.assertFalse(validate_url("javascript:alert(1)"))
        
        print("✅ URL验证测试通过")

    def test_format_response(self):
        """测试响应格式化功能"""
        print("🧪 测试响应格式化功能...")
        
        test_content = "这是一个测试内容"
        formatted = format_response(test_content)
        
        # 检查是否包含必要的元素
        self.assertIn("AI生成的开发计划", formatted)
        self.assertIn("生成时间", formatted)
        self.assertIn("Qwen2.5-72B-Instruct", formatted)
        self.assertIn(test_content, formatted)
        
        print("✅ 响应格式化测试通过")

    def test_extract_prompts_section(self):
        """测试提示词提取功能"""
        print("🧪 测试提示词提取功能...")
        
        test_content = """
        # 开发计划
        这是开发计划的内容
        
        # AI编程助手提示词
        这是编程提示词的内容
        """
        
        prompts = extract_prompts_section(test_content)
        self.assertIn("编程助手提示词", prompts)
        self.assertIn("编程提示词的内容", prompts)
        
        print("✅ 提示词提取测试通过")

    def test_create_temp_markdown_file(self):
        """测试临时文件创建功能"""
        print("🧪 测试临时文件创建功能...")
        
        test_content = "# 测试内容\n这是测试用的Markdown内容"
        temp_file_path = create_temp_markdown_file(test_content)
        
        # 检查文件是否创建成功
        self.assertTrue(os.path.exists(temp_file_path))
        self.assertTrue(temp_file_path.endswith('.md'))
        
        # 检查文件内容
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, test_content)
        
        # 清理临时文件
        os.unlink(temp_file_path)
        
        print("✅ 临时文件创建测试通过")

class TestEnvironmentConfiguration(unittest.TestCase):
    """环境配置测试类"""

    def test_environment_files(self):
        """测试环境配置文件"""
        print("🧪 测试环境配置文件...")
        
        # 检查必要文件是否存在
        required_files = [
            'requirements.txt',
            '.env.example',
            'app_config.yaml',
            'Dockerfile',
            'docker-compose.yml'
        ]
        
        for file_name in required_files:
            self.assertTrue(
                os.path.exists(file_name), 
                f"缺少必要文件: {file_name}"
            )
        
        print("✅ 环境配置文件测试通过")

    def test_requirements_file(self):
        """测试requirements.txt文件"""
        print("🧪 测试requirements.txt文件...")
        
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            
        # 检查必要依赖
        required_packages = ['gradio', 'requests', 'python-dotenv']
        for package in required_packages:
            self.assertIn(package, requirements)
        
        print("✅ requirements.txt测试通过")

class TestDockerConfiguration(unittest.TestCase):
    """Docker配置测试类"""

    def test_dockerfile_syntax(self):
        """测试Dockerfile语法"""
        print("🧪 测试Dockerfile语法...")
        
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()
            
        # 检查必要指令
        required_instructions = ['FROM', 'WORKDIR', 'COPY', 'RUN', 'EXPOSE', 'CMD']
        for instruction in required_instructions:
            self.assertIn(instruction, dockerfile_content)
        
        print("✅ Dockerfile语法测试通过")

def run_integration_test():
    """运行集成测试"""
    print("🧪 运行集成测试...")
    
    # 模拟API调用
    with patch('requests.post') as mock_post:
        # 配置模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "这是一个模拟的AI响应，包含完整的开发计划和编程提示词。"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        try:
            from app_optimized import generate_development_plan
            
            # 测试基本功能
            result = generate_development_plan(
                "我想开发一个基于AI的代码审查工具",
                ""
            )
            
            # 验证返回值
            plan, prompts, temp_file = result
            
            assert isinstance(plan, str), "开发计划应该是字符串"
            assert isinstance(prompts, str), "编程提示词应该是字符串"
            assert isinstance(temp_file, str), "临时文件路径应该是字符串"
            
            print("✅ 集成测试通过")
            
        except Exception as e:
            print(f"❌ 集成测试失败: {e}")
            return False
    
    return True

def main():
    """主测试函数"""
    print("🚀 开始VibeDoc功能测试\n")
    
    # 运行单元测试
    print("=" * 50)
    print("单元测试")
    print("=" * 50)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestVibeDocFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironmentConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestDockerConfiguration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 运行集成测试
    print("\n" + "=" * 50)
    print("集成测试")
    print("=" * 50)
    
    integration_success = run_integration_test()
    
    # 总结测试结果
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_count = total_tests - failures - errors
    
    print(f"✅ 成功: {success_count}/{total_tests}")
    
    if failures > 0:
        print(f"❌ 失败: {failures}")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if errors > 0:
        print(f"💥 错误: {errors}")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    print(f"🧪 集成测试: {'✅ 通过' if integration_success else '❌ 失败'}")
    
    # 检查整体测试结果
    all_passed = (failures == 0 and errors == 0 and integration_success)
    
    if all_passed:
        print("\n🎉 所有测试通过！项目已准备好部署。")
        return 0
    else:
        print("\n⚠️  存在测试失败，请检查并修复问题。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)