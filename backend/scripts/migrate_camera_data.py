#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头数据迁移脚本
迁移 camera_status.csv, camera_images.csv, camera_health.csv 到新的表结构
"""

import sys
import os
import csv
from datetime import datetime
from decimal import Decimal

# 添加 backend 目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db_models.db_session import db_session_factory
import db_models  # 导入所有模型
from db_models.camera import Camera, CameraImage, CameraHealth
from db_models.device import Device
from sqlalchemy import text


def migrate_cameras(session):
    """步骤1: 迁移 camera_status.csv 数据，创建 devices + cameras 记录"""
    print("=" * 60)
    print("步骤 1: 迁移摄像头设备数据 (camera_status.csv)")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/camera_status.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return {}, 0
    
    camera_id_map = {}  # 旧的 camera_id -> 新的 cameras.id
    success_count = 0
    skip_count = 0
    error_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                old_camera_id = int(row['camera_id'])
                
                # 构建唯一的 device_id (UUID格式)
                camera_device_id = f"camera_{old_camera_id}"
                
                # 检查 device 是否已存在
                existing_device = session.query(Device).filter(
                    Device.device_id == camera_device_id
                ).first()
                
                if existing_device:
                    # 检查对应的 camera 记录
                    existing_camera = session.query(Camera).filter(
                        Camera.device_id == existing_device.id
                    ).first()
                    if existing_camera:
                        camera_id_map[old_camera_id] = existing_camera.id
                        skip_count += 1
                        continue
                
                # 创建 Device 记录 (使用原生SQL以便设置ID)
                device_insert_sql = text("""
                    INSERT INTO devices (
                        device_id, name, description, ownership, device_type_id,
                        model, manufacturer, location, pond_id, status, control_mode
                    ) VALUES (
                        :device_id, :name, :description, 'own', 2,
                        'camera', 'unknown', :location, 1, :status, 'manual'
                    )
                """)
                
                session.execute(device_insert_sql, {
                    'device_id': camera_device_id,
                    'name': row['name'] if row['name'] else f'摄像头-{old_camera_id}',
                    'description': f"摄像头设备 - {row['name']}" if row['name'] else None,
                    'location': row['location'] if row['location'] else None,
                    'status': row['status'] if row['status'] else 'unknown'
                })
                session.flush()
                
                # 获取刚创建的 device.id
                new_device = session.query(Device).filter(
                    Device.device_id == camera_device_id
                ).first()
                
                if not new_device:
                    error_count += 1
                    print(f"  ⚠️  创建设备失败: camera_id={old_camera_id}")
                    continue
                
                # 创建 Camera 记录（只传必需参数）
                camera = Camera(
                    device_id=new_device.id,
                    connectivity=int(row['connectivity']) if row['connectivity'] else 0,
                    fps=int(row['fps']) if row['fps'] else 0,
                    recording=row['recording'].lower() == 'true' if row['recording'] else False,
                    night_vision=row['night_vision'].lower() == 'true' if row['night_vision'] else False,
                    motion_detection=row['motion_detection'].lower() == 'true' if row['motion_detection'] else False
                )
                
                # 设置可选字段（标记了 init=False）
                if row.get('quality'):
                    camera.quality = row['quality']
                if row.get('temperature'):
                    camera.temperature = Decimal(row['temperature'])
                if row.get('last_update'):
                    camera.last_update = int(row['last_update'])
                if row.get('last_update_time'):
                    camera.last_update_time = row['last_update_time']
                if row.get('resolution'):
                    camera.resolution = row['resolution']
                if row.get('codec'):
                    camera.codec = row['codec']
                
                session.add(camera)
                session.flush()
                
                # 保存映射关系
                camera_id_map[old_camera_id] = camera.id
                success_count += 1
                
            except Exception as e:
                error_count += 1
                session.rollback()
                print(f"  ❌ 处理记录失败 (camera_id={row.get('camera_id', '?')}): {e}")
                continue
    
    session.commit()
    
    print(f"\n  ✓ camera_status.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    
    return camera_id_map, success_count


def migrate_camera_images(session, camera_id_map):
    """步骤2: 迁移 camera_images.csv 数据"""
    print("\n" + "=" * 60)
    print("步骤 2: 迁移摄像头图片数据 (camera_images.csv)")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/camera_images.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    # 检查 batch_id=1 是否存在
    from db_models.batch import Batch
    batch_exists = session.query(Batch).filter(Batch.batch_id == 1).first() is not None
    if not batch_exists:
        print(f"  ⚠️  警告: batches 表中不存在 batch_id=1，将跳过 batch_id 字段")
    else:
        print(f"  ✓ 批次数据已就绪: batch_id=1")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    unmapped_cameras = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 检查是否已存在（根据 id）
                image_id = int(row['id'])
                existing = session.query(CameraImage).filter(CameraImage.id == image_id).first()
                if existing:
                    skip_count += 1
                    continue
                
                # 获取 camera_id 映射
                old_camera_id = int(row['camera_id'])
                new_camera_id = camera_id_map.get(old_camera_id)
                
                if not new_camera_id:
                    unmapped_cameras.add(old_camera_id)
                    error_count += 1
                    continue
                
                # 解析时间戳（毫秒转datetime）
                ts_utc = None
                if row['timestamp']:
                    try:
                        ts_ms = int(row['timestamp'])
                        ts_utc = datetime.fromtimestamp(ts_ms / 1000.0)
                    except:
                        pass
                
                if not ts_utc:
                    # 如果没有timestamp，尝试使用其他字段
                    if row['ts_utc']:
                        ts_utc = datetime.strptime(row['ts_utc'], '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        ts_utc = datetime.utcnow()
                
                # 创建 CameraImage 记录（只传必需参数）
                camera_image = CameraImage(
                    camera_id=new_camera_id,
                    pond_id=1,  # pool_id=4 映射到 pond_id=1
                    image_url=row['image_url'] if row['image_url'] else '',
                    ts_utc=ts_utc,
                    timestamp_str=row['timestamp_str'] if row['timestamp_str'] else '',
                    width=int(row['width']) if row['width'] and int(row['width']) > 0 else 1920,
                    height=int(row['height']) if row['height'] and int(row['height']) > 0 else 1080,
                    format=row['format'] if row['format'] else 'jpg',
                    size=int(row['size']) if row['size'] else 0,
                    fps=int(row['fps']) if row['fps'] else 0
                )
                
                # 设置可选字段（标记了 init=False）
                if row.get('batch_id') and batch_exists:
                    # 映射 batch_id: CSV中的2 -> 数据库中的1
                    csv_batch_id = int(row['batch_id'])
                    camera_image.batch_id = 1 if csv_batch_id == 2 else csv_batch_id
                if row.get('storage_uri'):
                    camera_image.storage_uri = row['storage_uri']
                if row.get('ts_local'):
                    try:
                        camera_image.ts_local = datetime.strptime(row['ts_local'], '%Y-%m-%d %H:%M:%S.%f')
                    except:
                        pass
                if row.get('codec'):
                    camera_image.codec = row['codec']
                if row.get('quality_flag'):
                    camera_image.quality_flag = row['quality_flag']
                if row.get('checksum'):
                    camera_image.checksum = row['checksum']
                
                session.add(camera_image)
                success_count += 1
                
                if success_count % 100 == 0:
                    session.flush()
                    print(f"  进度: 已处理 {success_count} 条记录...")
                    
            except Exception as e:
                error_count += 1
                session.rollback()
                if error_count <= 10:  # 只显示前10个错误
                    print(f"  ❌ 处理记录失败 (id={row.get('id', '?')}): {e}")
                continue
    
    session.commit()
    
    if unmapped_cameras:
        print(f"\n  ⚠️  未映射的摄像头ID: {sorted(unmapped_cameras)}")
    
    print(f"\n  ✓ camera_images.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    
    return success_count


def migrate_camera_health(session, camera_id_map):
    """步骤3: 迁移 camera_health.csv 数据"""
    print("\n" + "=" * 60)
    print("步骤 3: 迁移摄像头健康检查数据 (camera_health.csv)")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/camera_health.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    success_count = 0
    skip_count = 0
    error_count = 0
    unmapped_cameras = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 检查是否已存在（根据 id）
                health_id = int(row['id'])
                existing = session.query(CameraHealth).filter(CameraHealth.id == health_id).first()
                if existing:
                    skip_count += 1
                    continue
                
                # 获取 camera_id 映射
                old_camera_id = int(row['camera_id'])
                new_camera_id = camera_id_map.get(old_camera_id)
                
                if not new_camera_id:
                    unmapped_cameras.add(old_camera_id)
                    error_count += 1
                    continue
                
                # 创建 CameraHealth 记录（传所有必需参数）
                camera_health = CameraHealth(
                    camera_id=new_camera_id,
                    pond_id=1,  # pool_id=4 映射到 pond_id=1
                    health_status=row['health_status'] if row['health_status'] else '未知',
                    overall_score=Decimal(row['overall_score']) if row['overall_score'] else Decimal('0'),
                    connectivity_status=row['connectivity_status'] if row['connectivity_status'] else '未知',
                    connectivity_score=int(row['connectivity_score']) if row['connectivity_score'] else 0,
                    connectivity_message=row['connectivity_message'] if row['connectivity_message'] else '',
                    image_quality_status=row['image_quality_status'] if row['image_quality_status'] else '未知',
                    image_quality_score=int(row['image_quality_score']) if row['image_quality_score'] else 0,
                    image_quality_message=row['image_quality_message'] if row['image_quality_message'] else '',
                    hardware_status=row['hardware_status'] if row['hardware_status'] else '未知',
                    hardware_score=int(row['hardware_score']) if row['hardware_score'] else 0,
                    hardware_message=row['hardware_message'] if row['hardware_message'] else '',
                    storage_status=row['storage_status'] if row['storage_status'] else '未知',
                    storage_score=int(row['storage_score']) if row['storage_score'] else 0,
                    storage_message=row['storage_message'] if row['storage_message'] else '',
                    timestamp=int(row['timestamp']) if row['timestamp'] else 0,
                    last_check=row['last_check'] if row['last_check'] else ''
                )
                
                # 设置可选字段（标记了 init=False）
                if row.get('temperature'):
                    camera_health.temperature = Decimal(row['temperature'])
                if row.get('uptime_hours'):
                    camera_health.uptime_hours = int(row['uptime_hours'])
                
                session.add(camera_health)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                session.rollback()
                if error_count <= 10:  # 只显示前10个错误
                    print(f"  ❌ 处理记录失败 (id={row.get('id', '?')}): {e}")
                continue
    
    session.commit()
    
    if unmapped_cameras:
        print(f"\n  ⚠️  未映射的摄像头ID: {sorted(unmapped_cameras)}")
    
    print(f"\n  ✓ camera_health.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    
    return success_count


def verify_migration(session):
    """步骤4: 验证迁移结果"""
    print("\n" + "=" * 60)
    print("步骤 4: 验证迁移结果")
    print("=" * 60)
    
    # 统计各类数据
    camera_count = session.query(Camera).count()
    camera_image_count = session.query(CameraImage).count()
    camera_health_count = session.query(CameraHealth).count()
    camera_device_count = session.query(Device).filter(Device.device_type_id == 2).count()
    
    print(f"  ✓ 数据统计:")
    print(f"    - 摄像头设备 (devices, type=2): {camera_device_count} 个")
    print(f"    - 摄像头配置 (cameras): {camera_count} 个")
    print(f"    - 摄像头图片 (camera_images): {camera_image_count} 条")
    print(f"    - 摄像头健康检查 (camera_health): {camera_health_count} 条")
    
    # 时间范围统计
    print(f"\n  ✓ 数据时间范围:")
    
    # 摄像头图片时间范围
    result = session.query(CameraImage).order_by(CameraImage.ts_utc.asc()).first()
    if result:
        min_date = result.ts_utc
        result = session.query(CameraImage).order_by(CameraImage.ts_utc.desc()).first()
        max_date = result.ts_utc
        print(f"    - 摄像头图片: {min_date} ~ {max_date}")
    
    print()


def main():
    """主函数"""
    print("=" * 60)
    print("摄像头数据迁移脚本")
    print("=" * 60)
    print()
    
    try:
        with db_session_factory() as session:
            # 步骤1: 迁移摄像头设备
            camera_id_map, cameras_count = migrate_cameras(session)
            
            if cameras_count == 0 and len(camera_id_map) == 0:
                print("\n⚠️  没有摄像头数据需要迁移")
                return False
            
            # 步骤2: 迁移摄像头图片
            images_count = migrate_camera_images(session, camera_id_map)
            
            # 步骤3: 迁移摄像头健康检查
            health_count = migrate_camera_health(session, camera_id_map)
            
            # 步骤4: 验证迁移结果
            verify_migration(session)
            
            print("=" * 60)
            print("✅ 摄像头数据迁移成功完成！")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

