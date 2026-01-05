#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件上传路由蓝图
处理文件上传和转发功能
"""

from flask import Blueprint, request, jsonify
import logging
import time
import requests
from werkzeug.utils import secure_filename
import os

from config.settings import Config

# 创建蓝图
file_upload_bp = Blueprint('file_upload', __name__, url_prefix='/api/v1')

# 配置日志
logger = logging.getLogger(__name__)

# 允许的文件扩展名（可从配置文件读取，默认值）
# 支持通过环境变量 ALLOWED_FILE_EXTENSIONS 配置（逗号分隔）
_default_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'json', 'csv', 'xlsx', 'doc', 'docx', 'xls', 'ppt', 'pptx', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'xml', 'yaml', 'yml'}
_env_extensions = os.getenv('ALLOWED_FILE_EXTENSIONS', '')
if _env_extensions:
    ALLOWED_EXTENSIONS = {ext.strip().lower() for ext in _env_extensions.split(',') if ext.strip()}
else:
    ALLOWED_EXTENSIONS = _default_extensions


def allowed_file(filename):
    """
    检查文件扩展名是否允许
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否允许
    """
    if not filename or '.' not in filename:
        logger.debug(f"文件名无效或没有扩展名: {filename}")
        return False
    
    # 提取扩展名（最后一个点之后的部分）
    ext = filename.rsplit('.', 1)[1].lower()
    is_allowed = ext in ALLOWED_EXTENSIONS
    
    if not is_allowed:
        logger.debug(f"文件扩展名不在允许列表中: {ext} (文件名: {filename})")
    
    return is_allowed


@file_upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    接收前端发送的文件
    
    请求格式:   
        - Content-Type: multipart/form-data
        - 文件字段名: file (可通过配置修改)
    
    Returns:
        JSON格式的响应，包含上传结果和转发结果
    """
    try:
        # 检查是否有文件在请求中
        if 'file' not in request.files:
            return jsonify({
                "code": 400,
                "message": "未找到文件，请使用 'file' 作为文件字段名",
                "data": None
            }), 400
        
        file = request.files['file']
        
        # 检查文件名是否为空
        if file.filename == '':
            return jsonify({
                "code": 400,
                "message": "文件名为空",
                "data": None
            }), 400
        
        # 先保存原始文件名和扩展名
        original_filename = file.filename or 'blob'
        
        # 调试：记录原始文件信息
        logger.info(f"[DEBUG] 原始文件信息: filename='{file.filename}', name='{file.name}', content_type='{file.content_type}'")
        logger.info(f"[DEBUG] original_filename 初始值: '{original_filename}'")
        
        # 如果文件名包含路径分隔符，只取文件名部分（处理 curl 上传时包含路径的情况）
        if original_filename and original_filename != 'blob':
            # 提取文件名（最后一个路径分隔符之后的部分）
            if '/' in original_filename:
                path_parts = original_filename.rsplit('/', 1)
                if len(path_parts) > 1:
                    extracted_name = path_parts[-1]
                    logger.info(f"[DEBUG] 从路径中提取文件名: '{extracted_name}' (原路径: '{file.filename}')")
                    original_filename = extracted_name
            elif '\\' in original_filename:
                path_parts = original_filename.rsplit('\\', 1)
                if len(path_parts) > 1:
                    extracted_name = path_parts[-1]
                    logger.info(f"[DEBUG] 从路径中提取文件名: '{extracted_name}' (原路径: '{file.filename}')")
                    original_filename = extracted_name
        
        logger.info(f"[DEBUG] 路径提取后的 original_filename: '{original_filename}'")
        
        # 优先使用表单参数中的文件名（如果前端提供了）
        provided_filename = request.form.get('filename') or request.form.get('file_name')
        if provided_filename:
            # 如果提供了文件名，使用它（但需要验证扩展名）
            if '.' in provided_filename:
                original_filename = provided_filename
                logger.info(f"使用表单参数提供的文件名: {original_filename}")
            else:
                # 如果提供的文件名没有扩展名，尝试从原始文件名或推断获取扩展名
                if '.' in (file.filename or ''):
                    ext = (file.filename or '').rsplit('.', 1)[1].lower()
                    original_filename = f"{provided_filename}.{ext}"
                    logger.info(f"使用表单参数提供的文件名（添加扩展名）: {original_filename}")
        
        # 处理文件名为 "blob" 的情况（前端使用 Blob 对象时可能没有设置文件名）
        # 尝试从 Content-Type 或文件内容推断文件类型
        # 注意：只有在文件名确实是 "blob" 或没有扩展名时才推断
        needs_inference = (original_filename == 'blob' or not original_filename or '.' not in original_filename)
        logger.info(f"[DEBUG] 是否需要推断文件类型: {needs_inference} (original_filename='{original_filename}')")
        
        if needs_inference:
            content_type = file.content_type or ''
            inferred_ext = None
            
            # 方法1: 从 Content-Type 推断
            content_type_map = {
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'image/gif': 'gif',
                'application/pdf': 'pdf',
                'text/plain': 'txt',
                'text/csv': 'csv',
                'application/json': 'json',
                'application/zip': 'zip',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'application/msword': 'doc',
                'application/vnd.ms-excel': 'xls',
            }
            
            inferred_ext = content_type_map.get(content_type.split(';')[0].strip())
            
            # 方法2: 如果 Content-Type 是 application/octet-stream，尝试从文件内容检测
            if not inferred_ext and content_type == 'application/octet-stream':
                # 读取文件的前几个字节来检测文件类型（magic bytes）
                file.seek(0)
                file_header = file.read(16)
                file.seek(0)  # 重置文件指针
                
                # 常见文件类型的 magic bytes
                if file_header.startswith(b'\x89PNG\r\n\x1a\n'):
                    inferred_ext = 'png'
                elif file_header.startswith(b'\xff\xd8\xff'):
                    inferred_ext = 'jpg'
                elif file_header.startswith(b'GIF87a') or file_header.startswith(b'GIF89a'):
                    inferred_ext = 'gif'
                elif file_header.startswith(b'%PDF'):
                    inferred_ext = 'pdf'
                elif file_header.startswith(b'PK\x03\x04'):  # ZIP 文件（包括 docx, xlsx 等）
                    # 检查是否是 Office 文档
                    file.seek(0)
                    try:
                        # 尝试读取 ZIP 文件结构
                        import zipfile
                        import io
                        zip_data = io.BytesIO(file.read())
                        with zipfile.ZipFile(zip_data, 'r') as zf:
                            file_list = zf.namelist()
                            if 'word/' in str(file_list) or '[Content_Types].xml' in file_list:
                                inferred_ext = 'docx'
                            elif 'xl/' in str(file_list) or 'xl/workbook.xml' in file_list:
                                inferred_ext = 'xlsx'
                            elif 'ppt/' in str(file_list):
                                inferred_ext = 'pptx'
                            else:
                                inferred_ext = 'zip'
                    except:
                        inferred_ext = 'zip'
                    file.seek(0)
                elif file_header.startswith(b'\x50\x4b\x03\x04'):  # 另一种 ZIP 格式
                    inferred_ext = 'zip'
                elif file_header.startswith(b'{\x22') or file_header.startswith(b'{\n') or file_header.startswith(b'{\r'):
                    # JSON 文件
                    inferred_ext = 'json'
                elif file_header.startswith(b'<?xml'):
                    inferred_ext = 'xml'
                elif file_header.startswith(b'---') or file_header.startswith(b'%YAML'):
                    inferred_ext = 'yaml'
                else:
                    # 尝试检测文本文件
                    try:
                        file.seek(0)
                        sample = file.read(1024)
                        file.seek(0)
                        # 检查是否是文本文件
                        if sample.decode('utf-8', errors='ignore').isprintable():
                            # 检查是否是 CSV
                            if ',' in sample.decode('utf-8', errors='ignore')[:100]:
                                inferred_ext = 'csv'
                            else:
                                inferred_ext = 'txt'
                    except:
                        pass
                    file.seek(0)
            
            # 方法3: 从表单参数获取文件类型（如果前端提供了）
            if not inferred_ext:
                file_type_param = request.form.get('file_type') or request.form.get('extension')
                if file_type_param:
                    inferred_ext = file_type_param.strip().lstrip('.').lower()
                    if inferred_ext in ALLOWED_EXTENSIONS:
                        logger.info(f"从表单参数获取文件类型: {inferred_ext}")
            
            if inferred_ext:
                # 如果原始文件名是 "blob" 或没有扩展名，使用推断的扩展名
                if original_filename == 'blob' or '.' not in original_filename:
                    original_filename = f"blob.{inferred_ext}"
                    logger.info(f"[DEBUG] 推断文件类型: {content_type} -> {inferred_ext}, 新文件名: {original_filename}")
                else:
                    # 如果原始文件名已经有扩展名，保留原始文件名（不覆盖）
                    logger.info(f"[DEBUG] 保留原始文件名: '{original_filename}', 推断类型: {inferred_ext}（未使用，因为文件名已有扩展名）")
            else:
                # 如果无法推断，尝试从表单参数获取
                file_type_param = request.form.get('file_type') or request.form.get('extension') or request.form.get('file_extension')
                if file_type_param:
                    inferred_ext = file_type_param.strip().lstrip('.').lower()
                    if inferred_ext in ALLOWED_EXTENSIONS:
                        # 如果原始文件名是 "blob" 或没有扩展名，使用推断的扩展名
                        if original_filename == 'blob' or '.' not in original_filename:
                            original_filename = f"blob.{inferred_ext}"
                            logger.info(f"从表单参数获取文件类型: {inferred_ext}, 新文件名: {original_filename}")
                        else:
                            # 如果原始文件名已经有扩展名，保留原始文件名
                            logger.info(f"保留原始文件名: {original_filename}, 表单参数类型: {inferred_ext}（未使用）")
                    else:
                        logger.warning(f"表单参数指定的文件类型不在允许列表中: {inferred_ext}")
                
                if not inferred_ext:
                    logger.warning(f"无法从 Content-Type 或文件内容推断文件类型: {content_type}, 文件名: {original_filename}")
        
        # 检查文件扩展名（使用原始文件名，在secure_filename之前）
        if not allowed_file(original_filename):
            # 提取文件扩展名用于错误提示
            file_ext = ''
            if '.' in original_filename:
                file_ext = original_filename.rsplit('.', 1)[1].lower()
            
            logger.warning(f"不支持的文件类型: 文件名={original_filename}, 扩展名={file_ext}, Content-Type={file.content_type}")
            return jsonify({
                "code": 400,
                "message": f"不支持的文件类型: '{file_ext if file_ext else '无扩展名'}'，允许的类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                "data": {
                    "filename": original_filename,
                    "detected_extension": file_ext,
                    "content_type": file.content_type
                }
            }), 400
        
        # 提取并保存扩展名（在secure_filename之前）
        file_ext = ''
        if '.' in original_filename:
            file_ext = original_filename.rsplit('.', 1)[1].lower()
        
        # 获取安全的文件名（只处理文件名部分，保留扩展名）
        # secure_filename可能会移除中文等字符，导致扩展名丢失
        base_name = secure_filename(original_filename.rsplit('.', 1)[0]) if '.' in original_filename else secure_filename(original_filename)
        
        # 如果base_name为空（secure_filename移除了所有字符），使用时间戳作为文件名
        if not base_name or base_name.strip() == '':
            base_name = f"file_{int(time.time())}"
        
        # 重新组合文件名（保留原始扩展名）
        if file_ext:
            filename = f"{base_name}.{file_ext}"
        else:
            filename = base_name
        
        # 再次验证最终文件名
        if not allowed_file(filename):
            logger.error(f"文件名处理后验证失败: 原始={original_filename}, 处理后={filename}")
            return jsonify({
                "code": 400,
                "message": f"文件名处理失败，请使用英文文件名",
                "data": {
                    "original_filename": original_filename,
                    "processed_filename": filename
                }
            }), 400
        
        # 读取文件内容
        file_content = file.read()
        file_size = len(file_content)
        
        logger.info(f"收到文件上传请求: {filename}, 大小: {file_size} 字节")
        
        # 准备响应数据
        response_data = {
            "code": 200,
            "message": "文件上传成功",
            "data": {
                "filename": filename,
                "size": file_size,
                "forward": {
                    "enabled": False,
                    "url": None,
                    "success": None,
                    "error": None
                }
            }
        }
        
        # 如果配置了转发地址，则转发文件
        if Config.FILE_FORWARD_URL and Config.FILE_FORWARD_URL.lower() != 'none':
            try:
                forward_url = Config.FILE_FORWARD_URL
                logger.info(f"开始转发文件到: {forward_url}")
                
                # 准备转发请求
                # 需要重置文件指针以便重新读取
                file.seek(0)
                
                # 构建转发请求
                files = {
                    'file': (filename, file_content, file.content_type)
                }
                
                # 转发其他表单数据（如果有）
                data = {}
                for key, value in request.form.items():
                    data[key] = value
                
                # 发送转发请求
                forward_response = requests.post(
                    forward_url,
                    files=files,
                    data=data,
                    timeout=30  # 30秒超时
                )
                
                response_data["data"]["forward"]["enabled"] = True
                response_data["data"]["forward"]["url"] = forward_url
                response_data["data"]["forward"]["success"] = forward_response.status_code == 200
                response_data["data"]["forward"]["status_code"] = forward_response.status_code
                
                if forward_response.status_code == 200:
                    logger.info(f"文件转发成功: {filename} -> {forward_url}")
                    try:
                        response_data["data"]["forward"]["response"] = forward_response.json()
                    except:
                        response_data["data"]["forward"]["response"] = forward_response.text[:500]  # 限制响应长度
                else:
                    error_msg = f"转发失败，状态码: {forward_response.status_code}"
                    logger.warning(f"{error_msg}: {filename} -> {forward_url}")
                    response_data["data"]["forward"]["error"] = error_msg
                    try:
                        response_data["data"]["forward"]["response"] = forward_response.text[:500]
                    except:
                        pass
                        
            except requests.exceptions.Timeout:
                error_msg = "转发请求超时"
                logger.error(f"{error_msg}: {filename} -> {forward_url}")
                response_data["data"]["forward"]["enabled"] = True
                response_data["data"]["forward"]["url"] = forward_url
                response_data["data"]["forward"]["success"] = False
                response_data["data"]["forward"]["error"] = error_msg
                
            except requests.exceptions.RequestException as e:
                error_msg = f"转发请求异常: {str(e)}"
                logger.error(f"{error_msg}: {filename} -> {forward_url}")
                response_data["data"]["forward"]["enabled"] = True
                response_data["data"]["forward"]["url"] = forward_url
                response_data["data"]["forward"]["success"] = False
                response_data["data"]["forward"]["error"] = error_msg
                
            except Exception as e:
                error_msg = f"转发处理异常: {str(e)}"
                logger.error(f"{error_msg}: {filename}")
                response_data["data"]["forward"]["enabled"] = True
                response_data["data"]["forward"]["url"] = Config.FILE_FORWARD_URL
                response_data["data"]["forward"]["success"] = False
                response_data["data"]["forward"]["error"] = error_msg
        else:
            logger.info(f"未配置转发地址，跳过转发: {filename}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"文件上传处理异常: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500


@file_upload_bp.route('/upload/multiple', methods=['POST'])
def upload_multiple_files():
    """
    接收前端发送的多个文件
    
    请求格式:
        - Content-Type: multipart/form-data
        - 文件字段名: files[] (多个文件使用相同的字段名)
    
    Returns:
        JSON格式的响应，包含所有文件的上传结果和转发结果
    """
    try:
        # 检查是否有文件在请求中
        if 'files[]' not in request.files:
            return jsonify({
                "code": 400,
                "message": "未找到文件，请使用 'files[]' 作为文件字段名",
                "data": None
            }), 400
        
        files = request.files.getlist('files[]')
        
        if not files or all(f.filename == '' for f in files):
            return jsonify({
                "code": 400,
                "message": "文件列表为空",
                "data": None
            }), 400
        
        results = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # 检查文件扩展名
            if not allowed_file(file.filename):
                results.append({
                    "filename": file.filename,
                    "size": 0,
                    "error": f"不支持的文件类型"
                })
                continue
            
            # 获取安全的文件名
            filename = secure_filename(file.filename)
            
            # 读取文件内容
            file_content = file.read()
            file_size = len(file_content)
            
            logger.info(f"收到文件上传请求: {filename}, 大小: {file_size} 字节")
            
            # 准备响应数据
            file_result = {
                "filename": filename,
                "size": file_size,
                "forward": {
                    "enabled": False,
                    "url": None,
                    "success": None,
                    "error": None
                }
            }
            
            # 如果配置了转发地址，则转发文件
            if Config.FILE_FORWARD_URL and Config.FILE_FORWARD_URL.lower() != 'none':
                try:
                    forward_url = Config.FILE_FORWARD_URL
                    logger.info(f"开始转发文件到: {forward_url}")
                    
                    # 准备转发请求
                    files_data = {
                        'file': (filename, file_content, file.content_type)
                    }
                    
                    # 转发其他表单数据（如果有）
                    data = {}
                    for key, value in request.form.items():
                        data[key] = value
                    
                    # 发送转发请求
                    forward_response = requests.post(
                        forward_url,
                        files=files_data,
                        data=data,
                        timeout=30
                    )
                    
                    file_result["forward"]["enabled"] = True
                    file_result["forward"]["url"] = forward_url
                    file_result["forward"]["success"] = forward_response.status_code == 200
                    file_result["forward"]["status_code"] = forward_response.status_code
                    
                    if forward_response.status_code == 200:
                        logger.info(f"文件转发成功: {filename} -> {forward_url}")
                    else:
                        error_msg = f"转发失败，状态码: {forward_response.status_code}"
                        logger.warning(f"{error_msg}: {filename} -> {forward_url}")
                        file_result["forward"]["error"] = error_msg
                        
                except Exception as e:
                    error_msg = f"转发处理异常: {str(e)}"
                    logger.error(f"{error_msg}: {filename}")
                    file_result["forward"]["enabled"] = True
                    file_result["forward"]["url"] = Config.FILE_FORWARD_URL
                    file_result["forward"]["success"] = False
                    file_result["forward"]["error"] = error_msg
            else:
                logger.info(f"未配置转发地址，跳过转发: {filename}")
            
            results.append(file_result)
        
        return jsonify({
            "code": 200,
            "message": "文件上传成功",
            "data": {
                "files": results,
                "count": len(results)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"多文件上传处理异常: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": f"服务器内部错误: {str(e)}",
            "data": None
        }), 500





