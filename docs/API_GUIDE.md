# Tarkov.dev API 使用指南

## 📡 API 基础信息

**端点**: `https://api.tarkov.dev/graphql`  
**类型**: GraphQL  
**认证**: 无需 Token  
**限制**: 无官方限制（请合理使用）  
**文档**: https://api.tarkov.dev/

## 🔍 常用查询示例

### 1. 查询物品价格（按名称）

```graphql
query GetItemPrice {
  itemsByName(name: "Bitcoin") {
    name
    shortName
    avg24hPrice
    lastLowPrice
    changeLast48hPercent
    basePrice
    updated
    iconLink
    wikiLink
    sellFor {
      vendor {
        name
      }
      price
      currency
    }
    buyFor {
      vendor {
        name
      }
      price
      currency
    }
  }
}
```

### 2. 搜索物品（模糊匹配）

```graphql
query SearchItems {
  items(name: "AK") {
    id
    name
    shortName
    avg24hPrice
    iconLink
  }
}
```

### 3. 获取地图信息

```graphql
query GetMapData {
  maps {
    id
    name
    normalizedName
    wiki
    enemies
    spawns {
      zoneName
      position {
        x
        y
        z
      }
    }
    extracts {
      name
      faction
      position {
        x
        y
        z
      }
    }
  }
}
```

### 4. 获取任务信息

```graphql
query GetQuests {
  tasks {
    id
    name
    trader {
      name
    }
    map {
      name
    }
    objectives {
      id
      type
      description
    }
  }
}
```

## 🦀 Rust 实现示例

### 基础设置

```rust
// Cargo.toml 依赖
// reqwest = { version = "0.11", features = ["json"] }
// serde = { version = "1.0", features = ["derive"] }
// serde_json = "1.0"
// tokio = { version = "1", features = ["full"] }

use reqwest;
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Serialize, Deserialize)]
struct GraphQLResponse<T> {
    data: T,
}

#[derive(Debug, Serialize, Deserialize)]
struct ItemsResponse {
    #[serde(rename = "itemsByName")]
    items_by_name: Vec<Item>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Item {
    pub name: String,
    #[serde(rename = "shortName")]
    pub short_name: String,
    #[serde(rename = "avg24hPrice")]
    pub avg_24h_price: Option<u32>,
    #[serde(rename = "lastLowPrice")]
    pub last_low_price: Option<u32>,
    #[serde(rename = "changeLast48hPercent")]
    pub change_last_48h_percent: Option<f64>,
    #[serde(rename = "iconLink")]
    pub icon_link: Option<String>,
    #[serde(rename = "sellFor")]
    pub sell_for: Option<Vec<PriceInfo>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PriceInfo {
    pub vendor: Vendor,
    pub price: u32,
    pub currency: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Vendor {
    pub name: String,
}
```

### Tauri Command 实现

```rust
// src-tauri/src/commands/price.rs

use super::*;

const TARKOV_API_URL: &str = "https://api.tarkov.dev/graphql";

#[tauri::command]
pub async fn get_item_price(item_name: String) -> Result<Vec<Item>, String> {
    // 构建 GraphQL 查询
    let query = format!(
        r#"
        query {{
            itemsByName(name: "{}") {{
                name
                shortName
                avg24hPrice
                lastLowPrice
                changeLast48hPercent
                iconLink
                sellFor {{
                    vendor {{ name }}
                    price
                    currency
                }}
            }}
        }}
        "#,
        item_name
    );

    // 发送请求
    let client = reqwest::Client::new();
    let response = client
        .post(TARKOV_API_URL)
        .json(&json!({ "query": query }))
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    // 检查响应状态
    if !response.status().is_success() {
        return Err(format!("API 返回错误状态: {}", response.status()));
    }

    // 解析响应
    let result: GraphQLResponse<ItemsResponse> = response
        .json()
        .await
        .map_err(|e| format!("解析响应失败: {}", e))?;

    Ok(result.data.items_by_name)
}

#[tauri::command]
pub async fn search_items(keyword: String) -> Result<Vec<Item>, String> {
    let query = format!(
        r#"
        query {{
            items(name: "{}") {{
                name
                shortName
                avg24hPrice
                iconLink
            }}
        }}
        "#,
        keyword
    );

    let client = reqwest::Client::new();
    let response = client
        .post(TARKOV_API_URL)
        .json(&json!({ "query": query }))
        .send()
        .await
        .map_err(|e| format!("搜索失败: {}", e))?;

    let result: GraphQLResponse<ItemsResponse> = response
        .json()
        .await
        .map_err(|e| format!("解析失败: {}", e))?;

    Ok(result.data.items_by_name)
}
```

## ⚛️ React/TypeScript 调用示例

### 自定义 Hook

```typescript
// src/hooks/useTarkovAPI.ts

import { invoke } from '@tauri-apps/api/tauri';

export interface Item {
  name: string;
  shortName: string;
  avg24hPrice: number | null;
  lastLowPrice: number | null;
  changeLast48hPercent: number | null;
  iconLink: string | null;
  sellFor: PriceInfo[] | null;
}

export interface PriceInfo {
  vendor: { name: string };
  price: number;
  currency: string | null;
}

export function useTarkovAPI() {
  const getItemPrice = async (itemName: string): Promise<Item[]> => {
    try {
      const result = await invoke<Item[]>('get_item_price', { itemName });
      return result;
    } catch (error) {
      console.error('获取物品价格失败:', error);
      throw error;
    }
  };

  const searchItems = async (keyword: string): Promise<Item[]> => {
    try {
      const result = await invoke<Item[]>('search_items', { keyword });
      return result;
    } catch (error) {
      console.error('搜索物品失败:', error);
      throw error;
    }
  };

  return { getItemPrice, searchItems };
}
```

### React 组件使用

```tsx
// src/pages/PriceChecker.tsx

import { useState } from 'react';
import { useTarkovAPI } from '../hooks/useTarkovAPI';

export default function PriceChecker() {
  const [itemName, setItemName] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { getItemPrice } = useTarkovAPI();

  const handleSearch = async () => {
    if (!itemName.trim()) return;

    setLoading(true);
    setError('');

    try {
      const items = await getItemPrice(itemName);
      setResults(items);
    } catch (err) {
      setError('查询失败，请重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">物价查询</h1>
      
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={itemName}
          onChange={(e) => setItemName(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="输入物品名称..."
          className="flex-1 px-4 py-2 border rounded"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? '查询中...' : '查询'}
        </button>
      </div>

      {error && (
        <div className="text-red-500 mb-4">{error}</div>
      )}

      <div className="space-y-4">
        {results.map((item, index) => (
          <div key={index} className="p-4 border rounded bg-white shadow">
            <div className="flex items-center gap-4">
              {item.iconLink && (
                <img src={item.iconLink} alt={item.name} className="w-16 h-16" />
              )}
              <div className="flex-1">
                <h2 className="text-xl font-bold">{item.name}</h2>
                <p className="text-gray-600">{item.shortName}</p>
              </div>
            </div>
            
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">24h 平均价格</p>
                <p className="text-lg font-bold">
                  {item.avg24hPrice?.toLocaleString() || 'N/A'} ₽
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">当前最低价</p>
                <p className="text-lg font-bold">
                  {item.lastLowPrice?.toLocaleString() || 'N/A'} ₽
                </p>
              </div>
            </div>

            {item.changeLast48hPercent !== null && (
              <div className="mt-2">
                <span className={`text-sm ${item.changeLast48hPercent > 0 ? 'text-green-500' : 'text-red-500'}`}>
                  48h 变化: {item.changeLast48hPercent > 0 ? '+' : ''}{item.changeLast48hPercent.toFixed(2)}%
                </span>
              </div>
            )}

            {item.sellFor && item.sellFor.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-gray-600 mb-2">商人收购价:</p>
                <div className="space-y-1">
                  {item.sellFor.map((priceInfo, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span>{priceInfo.vendor.name}</span>
                      <span className="font-bold">{priceInfo.price.toLocaleString()} {priceInfo.currency || '₽'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

## 🚨 错误处理

### 常见错误及解决方案

1. **网络请求失败**
   - 检查网络连接
   - 验证 API 端点是否可访问

2. **解析错误**
   - 检查 GraphQL 查询语法
   - 验证响应数据结构

3. **超时**
   - 设置合理的超时时间
   - 实现重试机制

### Rust 错误处理示例

```rust
use std::time::Duration;

#[tauri::command]
pub async fn get_item_price_with_retry(
    item_name: String,
    max_retries: u32,
) -> Result<Vec<Item>, String> {
    let mut attempts = 0;
    
    loop {
        match try_get_item_price(&item_name).await {
            Ok(items) => return Ok(items),
            Err(e) => {
                attempts += 1;
                if attempts >= max_retries {
                    return Err(format!("重试 {} 次后仍然失败: {}", max_retries, e));
                }
                tokio::time::sleep(Duration::from_secs(1)).await;
            }
        }
    }
}

async fn try_get_item_price(item_name: &str) -> Result<Vec<Item>, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("创建客户端失败: {}", e))?;

    // ... 发送请求逻辑
}
```

## 📚 更多资源

- GraphQL Playground: https://api.tarkov.dev/
- Tarkov.dev 源码: https://github.com/the-hideout/tarkov-api
- GraphQL 文档: https://graphql.org/learn/

---

**提示**: 这个 API 完全免费且开源，但请合理使用，避免频繁请求导致服务器压力。
