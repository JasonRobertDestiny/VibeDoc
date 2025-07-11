#!/usr/bin/env python3
"""
VibeDoc 基础功能验证脚本
验证项目结构和基本配置是否正确
"""

import os
import sys
import json
import yaml

def check_file_exists(file_path, description=""):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✅ {description or file_path} - 存在")
        return True
    else:
        print(f"❌ {description or file_path} - 缺失")
        return False

def check_file_content(file_path, required_content, description=""):
    """检查文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        missing_content = []
        for item in required_content:
            if item not in content:
                missing_content.append(item)
        
        if missing_content:
            print(f"❌ {description or file_path} - 缺少内容: {missing_content}")
            return False
        else:
            print(f"✅ {description or file_path} - 内容完整")
            return True
            
    except Exception as e:
        print(f"❌ {description or file_path} - 读取失败: {e}")
        return False

def validate_project_structure():
    """验证项目结构"""
    print("🏗️  验证项目结构...")
    
    required_files = {
        'app.py': '主应用文件',
        'requirements.txt': 'Python依赖文件',
        'app_config.yaml': '应用配置文件',
        '.env.example': '环境变量示例文件',
        'Dockerfile': 'Docker镜像配置',
        'docker-compose.yml': 'Docker编排配置',
        'README.md': '项目说明文档',
        'DEPLOYMENT.md': '部署指南',
        'test_vibedoc.py': '测试脚本'
    }
    
    results = []
    for file_path, description in required_files.items():
        results.append(check_file_exists(file_path, description))
    
    return all(results)

def validate_requirements():
    """验证requirements.txt"""
    print("\n📦 验证Python依赖...")
    
    required_packages = [
        'gradio',
        'requests',
        'python-dotenv'
    ]
    
    return check_file_content('requirements.txt', required_packages, 'requirements.txt')

def validate_app_config():
    """验证应用配置"""
    print("\n⚙️  验证应用配置...")
    
    try:
        with open('app_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        required_fields = ['title', 'sdk', 'app_file']
        missing_fields = []
        
        for field in required_fields:
            if field not in config:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ app_config.yaml - 缺少字段: {missing_fields}")
            return False
        else:
            print("✅ app_config.yaml - 配置完整")
            
            # 检查关键配置值
            if config.get('sdk') == 'gradio':
                print("✅ SDK配置正确 (gradio)")
            else:
                print(f"⚠️  SDK配置可能有问题: {config.get('sdk')}")
            
            if 'Agent应用开发赛道' in config.get('title', ''):
                print("✅ 标题包含正确的赛道信息")
            else:
                print("⚠️  标题可能需要更新赛道信息")
            
            return True
            
    except yaml.YAMLError as e:
        print(f"❌ app_config.yaml - YAML格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ app_config.yaml - 读取失败: {e}")
        return False

def validate_env_example():
    """验证环境变量示例"""
    print("\n🔐 验证环境变量配置...")
    
    required_vars = [
        'SILICONFLOW_API_KEY',
        'NODE_ENV',
        'PORT'
    ]
    
    return check_file_content('.env.example', required_vars, '环境变量示例')

def validate_docker_config():
    """验证Docker配置"""
    print("\n🐳 验证Docker配置...")
    
    # 检查Dockerfile
    dockerfile_requirements = [
        'FROM python:3.11',
        'WORKDIR /app',
        'COPY requirements.txt',
        'RUN pip install',
        'EXPOSE 3000',
        'CMD ["python", "app.py"]'
    ]
    
    dockerfile_ok = check_file_content('Dockerfile', dockerfile_requirements, 'Dockerfile')
    
    # 检查docker-compose.yml
    compose_requirements = [
        'version:',
        'services:',
        'vibedoc:',
        'ports:'
    ]
    
    compose_ok = check_file_content('docker-compose.yml', compose_requirements, 'docker-compose.yml')
    
    return dockerfile_ok and compose_ok

def validate_documentation():
    """验证文档"""
    print("\n📚 验证文档...")
    
    # 检查README.md
    readme_requirements = [
        '# 🚀 VibeDoc',
        '魔塔MCP&Agent挑战赛2025',
        'Agent应用开发赛道',
        '## 🎯 项目简介'
    ]
    
    readme_ok = check_file_content('README.md', readme_requirements, 'README.md')
    
    # 检查DEPLOYMENT.md
    deployment_requirements = [
        '# 🚀 VibeDoc 部署指南',
        '魔塔ModelScope部署',
        'Docker部署',
        '环境配置'
    ]
    
    deployment_ok = check_file_content('DEPLOYMENT.md', deployment_requirements, 'DEPLOYMENT.md')
    
    return readme_ok and deployment_ok

def validate_python_syntax():
    """验证Python语法"""
    print("\n🐍 验证Python语法...")
    
    python_files = ['app.py', 'test_vibedoc.py']
    results = []
    
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单的语法检查
                compile(content, file_path, 'exec')
                print(f"✅ {file_path} - 语法正确")
                results.append(True)
                
            except SyntaxError as e:
                print(f"❌ {file_path} - 语法错误: {e}")
                results.append(False)
            except Exception as e:
                print(f"⚠️  {file_path} - 检查失败: {e}")
                results.append(False)
        else:
            print(f"❌ {file_path} - 文件不存在")
            results.append(False)
    
    return all(results)

def check_security_issues():
    """检查安全问题"""
    print("\n🔒 检查安全问题...")
    
    security_issues = []
    
    # 检查是否有硬编码的API密钥
    python_files = ['app.py']
    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查硬编码密钥模式
            if 'sk-' in content and 'os.environ' not in content.split('sk-')[1].split('\n')[0]:
                security_issues.append(f"{file_path}: 可能包含硬编码API密钥")
    
    if security_issues:
        for issue in security_issues:
            print(f"⚠️  {issue}")
        return False
    else:
        print("✅ 未发现明显的安全问题")
        return True

def main():
    """主验证函数"""
    print("🔍 VibeDoc 项目验证")
    print("=" * 50)
    
    # 运行所有验证
    validations = [
        ("项目结构", validate_project_structure),
        ("Python依赖", validate_requirements),
        ("应用配置", validate_app_config),
        ("环境变量", validate_env_example),
        ("Docker配置", validate_docker_config),
        ("文档完整性", validate_documentation),
        ("Python语法", validate_python_syntax),
        ("安全检查", check_security_issues)
    ]
    
    results = []
    for name, validation_func in validations:
        try:
            result = validation_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} - 验证失败: {e}")
            results.append((name, False))
    
    # 显示总结
    print("\n" + "=" * 50)
    print("📊 验证总结")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:15s} - {status}")
    
    print(f"\n总体结果: {passed}/{total} 项验证通过")
    
    if passed == total:
        print("\n🎉 项目验证完全通过！")
        print("✨ 项目已优化完成，可以部署使用")
        return 0
    else:
        print(f"\n⚠️  还有 {total - passed} 项需要修复")
        return 1

if __name__ == "__main__":
    try:
        import yaml
    except ImportError:
        print("⚠️  警告: 缺少pyyaml库，跳过YAML配置验证")
        # 创建一个简化的yaml模块
        class SimpleYAML:
            @staticmethod
            def safe_load(content):
                # 简单的YAML解析（仅用于基本验证）
                lines = content.strip().split('\n')
                result = {}
                for line in lines:
                    if ':' in line and not line.strip().startswith('#'):
                        key, value = line.split(':', 1)
                        result[key.strip()] = value.strip()
                return result
        
        yaml = SimpleYAML()
    
    exit_code = main()
    sys.exit(exit_code)