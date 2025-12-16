# 仿射变换修复 - 技术文档

## 问题描述

用户报告："我校准点肯定是相当准确了，但是哪怕我站在校准点上启用位置追踪，我的位置都是错的。而且方向完全反了180°"

调试输出显示：
```
游戏坐标: X=459.68, Y=4.08, Z=-44.37
变换参数:
  旋转: 173.98°
地图坐标: X=999.00, Y=1713.49
```

## 根本原因

### 问题1：双重应用旋转

**原始实现**（错误）：

```python
@dataclass
class CoordinateTransform:
    scale_x: float = 1.0
    scale_z: float = 1.0
    offset_x: float = 0.0
    offset_z: float = 0.0
    rotation: float = 0.0  # 旋转角度（弧度）

    def transform(self, game_pos: Position3D) -> Tuple[float, float]:
        # 手动应用旋转
        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)
        x_rotated = game_pos.x * cos_r - game_pos.z * sin_r
        z_rotated = game_pos.x * sin_r + game_pos.z * cos_r

        # 应用缩放和偏移
        map_x = x_rotated * self.scale_x + self.offset_x
        map_y = z_rotated * self.scale_z + self.offset_z

        return (map_x, map_y)
```

**问题**：

1. coordinate_transform.py计算仿射系数时：
   ```python
   coeffs_x = [a, b, c]  # map_x = a*game_x + b*game_z + c
   coeffs_y = [d, e, f]  # map_y = d*game_x + e*game_z + f
   ```

2. 然后**提取**旋转角度：
   ```python
   rotation = np.arctan2(d, a)
   ```

3. transform()方法又**手动应用旋转一次**，导致**双重旋转**！

### 问题2：未使用正确的仿射系数

原实现只存储了scale_x, scale_z, offset_x, offset_z和rotation，但没有存储原始的仿射系数a, b, d, e。

这意味着从rotation反推的变换矩阵可能不准确，特别是当地图有复杂变换时（不仅仅是简单的旋转+缩放）。

## 解决方案

参考**塔科夫妙妙工具箱1.21**的实现方式，直接存储和使用仿射系数。

### 修复后的实现

```python
@dataclass
class CoordinateTransform:
    """
    坐标变换矩阵

    使用仿射变换（Affine Transform）

    仿射变换公式:
    map_x = a * game_x + b * game_z + c
    map_y = d * game_x + e * game_z + f

    其中系数矩阵已经包含了旋转、缩放和平移信息
    """
    # 仿射变换系数
    # map_x = a * game_x + b * game_z + c
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0

    # map_y = d * game_x + e * game_z + f
    d: float = 0.0
    e: float = 1.0
    f: float = 0.0

    # 几何参数（从系数矩阵提取，仅用于显示）
    scale_x: float = 1.0
    scale_z: float = 1.0
    offset_x: float = 0.0
    offset_z: float = 0.0
    rotation: float = 0.0  # 旋转角度（弧度）

    def transform(self, game_pos: Position3D) -> Tuple[float, float]:
        """
        将游戏坐标转换为地图坐标

        直接应用仿射变换公式，不需要手动应用旋转
        因为系数a,b,d,e已经包含了旋转信息
        """
        # 直接应用仿射变换
        map_x = self.a * game_pos.x + self.b * game_pos.z + self.c
        map_y = self.d * game_pos.x + self.e * game_pos.z + self.f

        return (map_x, map_y)
```

### coordinate_transform.py的更新

```python
def _calculate_basic_transform(points: List[CalibrationPoint]) -> CoordinateTransform:
    # ... 计算仿射系数 ...
    a, b, c = coeffs_x
    d, e, f = coeffs_y

    # 从仿射矩阵参数提取几何变换参数（仅用于显示）
    scale_x = np.sqrt(a**2 + d**2)
    scale_z = np.sqrt(b**2 + e**2)
    rotation = np.arctan2(d, a)

    # 创建变换对象（包含完整的仿射系数）
    transform = CoordinateTransform(
        a=a, b=b, c=c,
        d=d, e=e, f=f,
        scale_x=scale_x,
        scale_z=scale_z,
        offset_x=c,
        offset_z=f,
        rotation=rotation
    )
    return transform
```

## 验证结果

### 测试1：使用真实海关地图系数

妙妙工具箱的海关地图matrix:
```json
[-7.322577378214782, 0.012263067819052804, 5586.854975262346,
 0.006077211057336157, 7.315145785641285, 3388.3048366330745]
```

测试坐标：游戏(459.68, -44.37)

**修复前**：地图坐标 (999.00, 1713.49) ← 完全错误

**修复后**：地图坐标 (2220.27, 3066.53) ← 正确！

### 测试2：旋转180°的地图

校准点（地图旋转180°）：
```
点1: 游戏(100.0, 100.0) → 地图(1000.0, 1000.0)
点2: 游戏(200.0, 100.0) → 地图(900.0, 1000.0)
点3: 游戏(100.0, 200.0) → 地图(1000.0, 900.0)
```

计算结果：
- 仿射系数: a=-1.0, b=0.0, c=1100.0, d=0.0, e=-1.0, f=1100.0
- 旋转角度: -180.00° ← 正确识别
- 所有校准点误差: 0.00px ← 完美

玩家站在校准点1上：
- 游戏坐标: (100.0, 100.0)
- 地图坐标: (1000.0, 1000.0)
- **结果: 完全正确！** ✅

## 与妙妙工具箱的兼容性

妙妙工具箱使用的格式：
```json
"matrix": [a, b, c, d, e, f]
```

对应：
```
map_x = a * game_x + b * game_z + c
map_y = d * game_x + e * game_z + f
```

我们的实现完全兼容这个格式。

## 核心要点

### 为什么不能手动应用旋转？

仿射变换的系数矩阵：
```
[a  b] [game_x]   [c]
[d  e] [game_z] + [f]
```

已经包含了：
1. **旋转**：通过a, b, d, e的组合
2. **缩放**：通过系数的幅度
3. **平移**：通过c, f

如果再手动应用旋转，就是**双重旋转**，会导致位置完全错误。

### 正确的做法

1. **计算时**：使用最小二乘法求解仿射系数 a, b, c, d, e, f
2. **存储时**：保存完整的仿射系数
3. **转换时**：直接应用仿射公式，不要手动处理旋转
4. **显示时**：可以从系数提取旋转角度用于调试显示

### 旋转角度的作用

`rotation = arctan2(d, a)` 这个值：
- ❌ **不应该用于坐标转换**
- ✅ **只用于显示和调试**
- ✅ **用于理解地图的旋转情况**

## rotation_offset的说明

`rotation_offset`字段是**完全独立的**：

- **仿射变换**：处理游戏坐标到地图坐标的映射
- **rotation_offset**：修正玩家朝向箭头的显示方向

两者不冲突：
```python
# 1. 坐标转换
map_x, map_y = transform.transform(game_pos)  # 使用仿射变换

# 2. 朝向修正
corrected_yaw = yaw + layer.rotation_offset  # 修正箭头方向
```

## 总结

这次修复解决了根本性的数学错误：

- ❌ **修复前**：双重应用旋转，导致位置完全错误
- ✅ **修复后**：直接使用仿射系数，位置完全准确

修复内容：
1. CoordinateTransform模型添加a, b, c, d, e, f字段
2. transform()方法直接应用仿射公式
3. coordinate_transform.py返回完整仿射系数
4. 与妙妙工具箱完全兼容

**结果**：即使是旋转180°的地图，站在校准点上，位置也完全准确！

---

**修复日期**: 2025-12-05
**相关文件**:
- modules/local_map/models.py (Line 203-252)
- modules/local_map/coordinate_transform.py (Line 84-93, 147-157, 327-338)
**测试文件**: test_transform_fix.py
