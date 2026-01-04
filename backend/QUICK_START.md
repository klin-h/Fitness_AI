# PostgreSQL 快速开始指南

## 🚀 5分钟快速设置

### 1. 安装PostgreSQL

**Windows:**
- 下载安装包: https://www.postgresql.org/download/windows/
- 安装时记住设置的postgres用户密码（默认端口5432）

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. 创建数据库

打开命令行/终端，运行：

```bash
# 创建数据库
createdb -U postgres fitnessai

# 如果提示需要密码，输入postgres用户的密码
# 如果postgres用户没有密码，可以设置：
psql -U postgres
ALTER USER postgres PASSWORD 'postgres';
\q
```

### 3. 配置环境变量（可选）

在 `backend` 目录创建 `.env` 文件：

```env
# PostgreSQL数据库连接
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fitnessai

# AI配置（可选）
ZHIPU_API_KEY=your_api_key_here
```

**注意**: 如果不创建.env文件，系统会使用默认配置：
- 用户名: postgres
- 密码: postgres
- 主机: localhost
- 端口: 5432
- 数据库: fitnessai

### 4. 安装Python依赖

```bash
cd backend
pip install -r requirements.txt
```

### 5. 初始化数据库

```bash
python init_database.py
```

这个脚本会：
- ✅ 创建所有数据库表
- ✅ 自动迁移现有JSON数据（如果有）
- ✅ 验证数据库连接

### 6. 启动应用

```bash
python app.py
```

## ✅ 验证安装

运行以下命令测试数据库连接：

```bash
python -c "from app import app; from database import db; app.app_context().push(); print('✅ 数据库连接成功！')"
```

## 🔧 常见问题

### 问题1: 连接被拒绝

**错误**: `could not connect to server: Connection refused`

**解决**:
```bash
# 检查PostgreSQL是否运行
# Windows: 打开"服务"管理器，找到PostgreSQL服务并启动
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

### 问题2: 数据库不存在

**错误**: `database "fitnessai" does not exist`

**解决**:
```bash
createdb -U postgres fitnessai
```

### 问题3: 认证失败

**错误**: `password authentication failed`

**解决**:
1. 检查 `.env` 文件中的密码是否正确
2. 或者重置postgres密码：
```sql
psql -U postgres
ALTER USER postgres PASSWORD 'your_password';
\q
```

### 问题4: 权限不足

**错误**: `permission denied`

**解决**:
```sql
psql -U postgres -d fitnessai
GRANT ALL PRIVILEGES ON DATABASE fitnessai TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
\q
```

## 📊 数据库管理

### 查看数据库

```bash
psql -U postgres -d fitnessai
```

### 常用SQL命令

```sql
-- 查看所有表
\dt

-- 查看表结构
\d users

-- 查看数据
SELECT * FROM users LIMIT 10;

-- 退出
\q
```

### 备份数据库

```bash
pg_dump -U postgres fitnessai > backup.sql
```

### 恢复数据库

```bash
psql -U postgres fitnessai < backup.sql
```

## 🌐 部署到服务器

### 生产环境配置

1. **修改数据库连接字符串**

   在服务器上创建 `.env` 文件：
   ```env
   DATABASE_URL=postgresql://username:password@server_ip:5432/fitnessai
   ```

2. **安全建议**
   - 使用强密码
   - 限制数据库访问IP
   - 启用SSL连接
   - 定期备份

3. **迁移数据**

   从本地导出数据：
   ```bash
   pg_dump -U postgres fitnessai > production_backup.sql
   ```

   在服务器上导入：
   ```bash
   psql -U username -d fitnessai < production_backup.sql
   ```

## 🎉 完成！

现在你的应用已经使用PostgreSQL数据库了！

所有数据都会存储在PostgreSQL中，未来迁移到服务器时只需要：
1. 在服务器上安装PostgreSQL
2. 创建数据库
3. 修改 `.env` 文件中的 `DATABASE_URL`
4. 运行 `python init_database.py`
5. 导入数据（如果需要）

