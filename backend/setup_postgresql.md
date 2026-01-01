# PostgreSQL 数据库设置指南

## 📋 前置要求

1. **安装PostgreSQL**
   - Windows: 下载并安装 [PostgreSQL官方安装包](https://www.postgresql.org/download/windows/)
   - macOS: `brew install postgresql`
   - Linux (Ubuntu/Debian): `sudo apt-get install postgresql postgresql-contrib`

2. **启动PostgreSQL服务**
   - Windows: 服务会自动启动，或通过"服务"管理器启动
   - macOS: `brew services start postgresql`
   - Linux: `sudo systemctl start postgresql`

## 🚀 快速设置

### 方法一：使用默认配置（推荐）

1. **创建数据库**
   ```bash
   # Windows (使用pgAdmin或命令行)
   createdb -U postgres fitnessai
   
   # macOS/Linux
   createdb -U postgres fitnessai
   ```

2. **设置密码**（如果postgres用户没有密码）
   ```bash
   psql -U postgres
   ALTER USER postgres PASSWORD 'postgres';
   \q
   ```

3. **配置环境变量**
   
   在 `backend/.env` 文件中添加：
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fitnessai
   ```
   
   或者使用默认配置（已在代码中设置）

4. **安装Python依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

5. **初始化数据库**
   ```bash
   python init_database.py
   ```

### 方法二：自定义配置

1. **创建数据库和用户**
   ```sql
   -- 登录PostgreSQL
   psql -U postgres
   
   -- 创建数据库
   CREATE DATABASE fitnessai;
   
   -- 创建用户（可选）
   CREATE USER fitnessai_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE fitnessai TO fitnessai_user;
   
   -- 退出
   \q
   ```

2. **配置连接字符串**
   
   在 `backend/.env` 文件中：
   ```env
   DATABASE_URL=postgresql://fitnessai_user:your_password@localhost:5432/fitnessai
   ```

## 🔧 数据库迁移

### 从JSON文件迁移数据

如果之前使用JSON文件存储数据，运行迁移脚本：

```bash
cd backend
python init_database.py
```

脚本会自动：
1. 创建所有数据库表
2. 从JSON文件迁移现有数据
3. 保持数据完整性

### 迁移后的JSON文件

迁移完成后，JSON文件会被保留作为备份。你可以：
- 保留作为备份
- 删除（建议先确认数据库数据正确）

## 📊 数据库管理

### 使用psql命令行工具

```bash
# 连接到数据库
psql -U postgres -d fitnessai

# 查看所有表
\dt

# 查看表结构
\d users

# 查看数据
SELECT * FROM users LIMIT 10;

# 退出
\q
```

### 使用pgAdmin（图形界面）

1. 打开pgAdmin
2. 连接到PostgreSQL服务器
3. 展开数据库 → fitnessai
4. 查看和管理数据

## 🌐 部署到服务器

### 生产环境配置

1. **修改数据库连接**
   
   在服务器上创建 `.env` 文件：
   ```env
   DATABASE_URL=postgresql://username:password@server_ip:5432/fitnessai
   ```

2. **安全建议**
   - 使用强密码
   - 限制数据库访问IP
   - 启用SSL连接（如果支持）
   - 定期备份数据库

3. **备份数据库**
   ```bash
   pg_dump -U postgres fitnessai > backup.sql
   ```

4. **恢复数据库**
   ```bash
   psql -U postgres fitnessai < backup.sql
   ```

## 🔍 常见问题

### 1. 连接被拒绝

**错误**: `could not connect to server: Connection refused`

**解决**:
- 检查PostgreSQL服务是否运行
- 检查端口是否正确（默认5432）
- 检查防火墙设置

### 2. 认证失败

**错误**: `password authentication failed`

**解决**:
- 检查用户名和密码是否正确
- 检查 `pg_hba.conf` 配置文件
- 确认用户权限

### 3. 数据库不存在

**错误**: `database "fitnessai" does not exist`

**解决**:
```bash
createdb -U postgres fitnessai
```

### 4. 权限不足

**错误**: `permission denied`

**解决**:
```sql
GRANT ALL PRIVILEGES ON DATABASE fitnessai TO your_username;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
```

## 📝 环境变量配置

创建 `backend/.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fitnessai

# AI配置（可选）
ZHIPU_API_KEY=your_api_key_here
```

## ✅ 验证安装

运行以下命令验证数据库连接：

```bash
cd backend
python -c "from app import app; from database import db; app.app_context().push(); db.create_all(); print('✅ 数据库连接成功！')"
```

## 🎉 完成

设置完成后，启动应用：

```bash
python app.py
```

应用会自动连接到PostgreSQL数据库！

