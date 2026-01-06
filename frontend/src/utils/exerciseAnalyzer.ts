/**
 * 运动分析器
 * 基于 MediaPipe 姿态关键点实现不同运动的判定逻辑
 */

export interface Landmark {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
}

export interface ExerciseAnalysis {
  isCorrect: boolean;
  score: number;
  feedback: string;
  count?: number;
  duration?: number; // 用于平板支撑
}

/**
 * 计算三个点之间的角度（度）
 * 使用点积方法，更准确
 */
export function calculateAngle(
  point1: Landmark,
  point2: Landmark,
  point3: Landmark
): number {
  // 计算向量
  const ba = [point1.x - point2.x, point1.y - point2.y];
  const bc = [point3.x - point2.x, point3.y - point2.y];
  
  // 计算点积
  const dotProduct = ba[0] * bc[0] + ba[1] * bc[1];
  
  // 计算向量长度
  const baLength = Math.sqrt(ba[0] ** 2 + ba[1] ** 2);
  const bcLength = Math.sqrt(bc[0] ** 2 + bc[1] ** 2);
  
  // 计算夹角（弧度）
  try {
    let cosAngle = dotProduct / (baLength * bcLength);
    // 防止浮点数计算导致的越界
    cosAngle = Math.max(Math.min(cosAngle, 1.0), -1.0);
    const angleRad = Math.acos(cosAngle);
    
    // 转换为角度
    return (angleRad * 180.0) / Math.PI;
  } catch (e) {
    return 180.0; // 如果计算出错，返回180度
  }
}

/**
 * 计算两点之间的距离
 */
export function calculateDistance(
  point1: Landmark,
  point2: Landmark
): number {
  return Math.sqrt(
    Math.pow(point2.x - point1.x, 2) + Math.pow(point2.y - point1.y, 2)
  );
}

/**
 * 深蹲分析器
 * 优化版本：添加状态稳定性检测和冷却机制
 */
export class SquatAnalyzer {
  private squatCount = 0;
  private lastState: 'up' | 'down' = 'up';
  private inSquatPosition = false;
  private readonly angleThreshold = 140; // 角度阈值，更容易判定为下蹲
  private readonly standingThreshold = 140; // 站立角度阈值
  
  // 状态稳定性跟踪
  private consecutiveUpFrames = 0;   // 连续站立帧数
  private consecutiveDownFrames = 0; // 连续下蹲帧数
  private requiredFrames = 2;        // 需要连续帧数来确认状态
  private stateChangedFrames = 0;   // 状态保持的帧数
  
  // 冷却机制
  private cooldownCounter = 0;
  private readonly cooldownFrames = 10; // 计数后的冷却时间（帧数）

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    // 检查可见性 - 至少有一侧可见即可
    const leftHip = landmarks[23];
    const leftKnee = landmarks[25];
    const leftAnkle = landmarks[27];
    const rightHip = landmarks[24];
    const rightKnee = landmarks[26];
    const rightAnkle = landmarks[28];
    
    const leftVisible = leftHip?.visibility && leftHip.visibility >= 0.5 && 
                       leftKnee?.visibility && leftKnee.visibility >= 0.5 &&
                       leftAnkle?.visibility && leftAnkle.visibility >= 0.5;
    const rightVisible = rightHip?.visibility && rightHip.visibility >= 0.5 && 
                        rightKnee?.visibility && rightKnee.visibility >= 0.5 &&
                        rightAnkle?.visibility && rightAnkle.visibility >= 0.5;

    if (!leftVisible && !rightVisible) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保下半身在摄像头范围内',
        count: this.squatCount,
      };
    }

    // 计算膝盖角度 - 优先使用可见性更好的一侧
    let kneeAngle = 180.0;
    const leftVisibility = (leftHip?.visibility || 0) + 
                          (leftKnee?.visibility || 0) + 
                          (leftAnkle?.visibility || 0);
    const rightVisibility = (rightHip?.visibility || 0) + 
                           (rightKnee?.visibility || 0) + 
                           (rightAnkle?.visibility || 0);

    if (leftVisibility > rightVisibility && leftVisible && leftHip && leftKnee && leftAnkle) {
      kneeAngle = calculateAngle(leftHip, leftKnee, leftAnkle);
    } else if (rightVisible && rightHip && rightKnee && rightAnkle) {
      kneeAngle = calculateAngle(rightHip, rightKnee, rightAnkle);
    } else if (leftVisible && leftHip && leftKnee && leftAnkle) {
      kneeAngle = calculateAngle(leftHip, leftKnee, leftAnkle);
    }

    // 确定当前状态
    const currentState = this.detectSquatState(kneeAngle);

    // 更新连续帧计数
    if (currentState === 'up') {
      this.consecutiveUpFrames++;
      this.consecutiveDownFrames = 0;
    } else if (currentState === 'down') {
      this.consecutiveDownFrames++;
      this.consecutiveUpFrames = 0;
    }

    // 状态判断 - 需要连续多帧才确认状态
    let confirmedState = this.lastState;
    if (this.consecutiveUpFrames >= this.requiredFrames) {
      confirmedState = 'up';
    } else if (this.consecutiveDownFrames >= this.requiredFrames) {
      confirmedState = 'down';
    }

    // 更新计数
    const countUpdated = this.updateCount(confirmedState);

    // 生成反馈
    let feedback = '准备开始深蹲';
    if (confirmedState === 'down') {
      feedback = '很好！下蹲姿势正确，请站起来完成动作';
    } else {
      feedback = '站立姿势正确，请尝试下蹲';
    }

    // 计算得分和正确性
    let score = 50;
    let isCorrect = false;
    
    if (confirmedState === 'down') {
      // 下蹲状态：角度越小（蹲得越低）越好，但要在合理范围内（60-140度）
      score = Math.max(70, 100 - Math.max(0, kneeAngle - 90));
      isCorrect = kneeAngle < 120; // 角度小于120度认为是正确的下蹲
    } else {
      // 站立状态：角度越大（站得越直）越好
      score = Math.min(100, Math.max(70, kneeAngle));
      isCorrect = kneeAngle > 150; // 角度大于150度认为是正确的站立
    }

    return {
      isCorrect,
      score: Math.round(score),
      feedback,
      count: this.squatCount,
    };
  }

  private detectSquatState(kneeAngle: number): 'up' | 'down' {
    if (kneeAngle < this.angleThreshold) {
      return 'down';
    } else if (kneeAngle > this.standingThreshold) {
      return 'up';
    } else {
      // 在过渡区域，保持上一个状态，防止抖动
      return this.lastState;
    }
  }

  private updateCount(currentState: 'up' | 'down'): boolean {
    let countUpdated = false;

    // 冷却计数器处理
    if (this.cooldownCounter > 0) {
      this.cooldownCounter--;
    }

    // 状态变化检测
    if (currentState !== this.lastState) {
      if (this.stateChangedFrames >= 3) { // 确保之前的状态是稳定的
        if (this.lastState !== 'down' && currentState === 'down' && this.cooldownCounter === 0) {
          // 从其他状态变为下蹲状态
          this.inSquatPosition = true;
        } else if (this.lastState === 'down' && currentState === 'up' && this.inSquatPosition) {
          // 从下蹲状态变为起立状态
          if (this.cooldownCounter === 0) {
            this.squatCount++;
            countUpdated = true;
            this.cooldownCounter = this.cooldownFrames; // 设置冷却时间
          }
          this.inSquatPosition = false;
        }
        this.stateChangedFrames = 0;
      }
    } else {
      // 同一状态下累加帧数
      this.stateChangedFrames++;
    }

    this.lastState = currentState;
    return countUpdated;
  }

  reset(): void {
    this.squatCount = 0;
    this.inSquatPosition = false;
    this.lastState = 'up';
    this.consecutiveUpFrames = 0;
    this.consecutiveDownFrames = 0;
    this.stateChangedFrames = 0;
    this.cooldownCounter = 0;
  }
}

/**
 * 俯卧撑分析器
 * 优化版本：添加状态稳定性检测和冷却机制
 */
export class PushupAnalyzer {
  private pushupCount = 0;
  private lastState: 'up' | 'down' = 'up';
  private inDownPosition = false;
  private readonly angleThreshold = 115; // 弯曲角度阈值，小于这个角度被视为下降
  private readonly straightThreshold = 155; // 伸直角度阈值，大于这个角度被视为上升
  
  // 状态稳定性跟踪
  private consecutiveUpFrames = 0;   // 连续上升帧数
  private consecutiveDownFrames = 0; // 连续下降帧数
  private requiredFrames = 5;        // 要求更多帧数来确认状态
  private stateChangedFrames = 0;    // 状态保持的帧数
  
  // 冷却机制
  private cooldownCounter = 0;
  private readonly cooldownFrames = 15; // 冷却时间（帧数）

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftElbow = landmarks[13];
    const rightElbow = landmarks[14];
    
    // 检查可见性 - 至少有一侧可见即可
    const leftVisible = leftShoulder?.visibility && leftShoulder.visibility >= 0.5 && 
                       leftElbow?.visibility && leftElbow.visibility >= 0.5;
    const rightVisible = rightShoulder?.visibility && rightShoulder.visibility >= 0.5 && 
                        rightElbow?.visibility && rightElbow.visibility >= 0.5;

    if (!leftVisible && !rightVisible || !leftShoulder || !rightShoulder || !leftElbow || !rightElbow) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保上半身在摄像头范围内',
        count: this.pushupCount,
      };
    }
    
    if (!leftShoulder || !rightShoulder || !leftElbow || !rightElbow) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保上半身在摄像头范围内',
        count: this.pushupCount,
      };
    }
    
    // 尝试获取手腕，但不要求必须可见
    const leftWrist = landmarks[15]?.visibility && landmarks[15].visibility >= 0.5 ? landmarks[15] : null;
    const rightWrist = landmarks[16]?.visibility && landmarks[16].visibility >= 0.5 ? landmarks[16] : null;

    // 计算手臂角度
    let avgArmAngle = 180.0;
    const armAngles: number[] = [];

    if (leftWrist) {
      const leftArmAngle = calculateAngle(leftShoulder, leftElbow, leftWrist);
      armAngles.push(leftArmAngle);
    }

    if (rightWrist) {
      const rightArmAngle = calculateAngle(rightShoulder, rightElbow, rightWrist);
      armAngles.push(rightArmAngle);
    }

    if (armAngles.length > 0) {
      avgArmAngle = armAngles.reduce((a, b) => a + b, 0) / armAngles.length;
    }

    // 确定当前状态
    const currentState = this.detectPushupState(avgArmAngle);

    // 更新连续帧计数
    if (currentState === 'up') {
      this.consecutiveUpFrames++;
      this.consecutiveDownFrames = 0;
    } else if (currentState === 'down') {
      this.consecutiveDownFrames++;
      this.consecutiveUpFrames = 0;
    }

    // 状态判断 - 需要连续多帧才确认状态
    let confirmedState = this.lastState;
    if (this.consecutiveUpFrames >= this.requiredFrames) {
      confirmedState = 'up';
    } else if (this.consecutiveDownFrames >= this.requiredFrames) {
      confirmedState = 'down';
    }

    // 更新计数
    const countUpdated = this.updatePushupCount(confirmedState);

    // 生成反馈
    let feedback = '准备开始俯卧撑';
    if (confirmedState === 'down') {
      feedback = '已下降，请向上推起';
    } else {
      feedback = '已上升，请下降';
    }

    // 计算得分和正确性
    let score = 50;
    let isCorrect = false;
    
    if (confirmedState === 'down') {
      // 下压状态：角度越小（压得越低）越好，但要在合理范围内（70-115度）
      score = Math.max(60, 100 - Math.max(0, avgArmAngle - 90));
      isCorrect = avgArmAngle < 100; // 角度小于100度认为是正确的下压
    } else {
      // 上升状态：角度越大（手臂越直）越好
      score = Math.min(100, Math.max(60, avgArmAngle));
      isCorrect = avgArmAngle > 150; // 角度大于150度认为是正确的上升
    }

    return {
      isCorrect,
      score: Math.round(score),
      feedback,
      count: this.pushupCount,
    };
  }

  private detectPushupState(armAngle: number): 'up' | 'down' {
    if (armAngle < this.angleThreshold) {
      return 'down';
    } else if (armAngle > this.straightThreshold) {
      return 'up';
    } else {
      // 在过渡区域，保持上一个状态，防止抖动
      return this.lastState;
    }
  }

  private updatePushupCount(currentState: 'up' | 'down'): boolean {
    let countUpdated = false;

    // 冷却计数器处理
    if (this.cooldownCounter > 0) {
      this.cooldownCounter--;
    }

    // 状态变化检测
    if (currentState !== this.lastState) {
      if (this.stateChangedFrames >= 3) { // 确保之前的状态是稳定的
        if (this.lastState !== 'down' && currentState === 'down' && this.cooldownCounter === 0) {
          // 从其他状态变为下降状态
          this.inDownPosition = true;
        } else if (this.lastState === 'down' && currentState === 'up' && this.inDownPosition) {
          // 从下降状态变为上升状态
          if (this.cooldownCounter === 0) {
            this.pushupCount++;
            countUpdated = true;
            this.cooldownCounter = this.cooldownFrames; // 设置冷却时间
          }
          this.inDownPosition = false;
        }
        this.stateChangedFrames = 0;
      }
    } else {
      // 同一状态下累加帧数
      this.stateChangedFrames++;
    }

    this.lastState = currentState;
    return countUpdated;
  }

  reset(): void {
    this.pushupCount = 0;
    this.inDownPosition = false;
    this.lastState = 'up';
    this.consecutiveUpFrames = 0;
    this.consecutiveDownFrames = 0;
    this.stateChangedFrames = 0;
    this.cooldownCounter = 0;
  }
}

/**
 * 平板支撑分析器
 * 优化版本：添加稳定性检测和抖动过滤
 */
export class PlankAnalyzer {
  private plankDuration = 0; // 按帧计数
  private isInPlank = false;
  private readonly bodyAlignmentTolerance = 0.2; // 身体直线度容差
  private readonly elbowAngleThreshold = 120; // 肘部弯曲角度阈值
  
  // 状态稳定性跟踪
  private stableFrames = 0;
  private readonly minStableFrames = 10; // 需要至少10帧稳定才算有效平板支撑
  
  // 抖动检测
  private unstableFrames = 0;
  private readonly maxUnstableFrames = 5; // 允许的最大不稳定帧数
  
  // 假设30fps
  private readonly fps = 30;

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftElbow = landmarks[13];
    const rightElbow = landmarks[14];
    
    // 检查可见性 - 至少有一侧可见即可
    const leftVisible = leftShoulder?.visibility && leftShoulder.visibility >= 0.5 && 
                       leftElbow?.visibility && leftElbow.visibility >= 0.5;
    const rightVisible = rightShoulder?.visibility && rightShoulder.visibility >= 0.5 && 
                        rightElbow?.visibility && rightElbow.visibility >= 0.5;

    if (!leftVisible && !rightVisible || !leftShoulder || !rightShoulder || !leftElbow || !rightElbow) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保上半身在摄像头范围内',
        duration: this.plankDuration / this.fps, // 转换为秒
      };
    }
    
    // 尝试获取髋部，但不要求必须可见
    const leftHip = landmarks[23]?.visibility && landmarks[23].visibility >= 0.5 ? landmarks[23] : null;
    const rightHip = landmarks[24]?.visibility && landmarks[24].visibility >= 0.5 ? landmarks[24] : null;

    // 检查手肘是否弯曲（平板支撑姿势）
    // 简化：检查肘部是否在肩部下方
    const elbowsUnderShoulders = (leftElbow.y > leftShoulder.y && rightElbow.y > rightShoulder.y);
    
    // 简化判断，只要肘部在肩部下方就认为姿势正确
    const isCorrectForm = elbowsUnderShoulders;

    // 更新状态 - 需要更稳定的判断，增加抖动检测
    if (isCorrectForm) {
      this.stableFrames++;
      this.unstableFrames = 0; // 重置不稳定帧数
      
      if (this.stableFrames >= this.minStableFrames) {
        if (!this.isInPlank) {
          this.isInPlank = true;
        }
        this.plankDuration++; // 增加持续时间（按帧计数）
      }
    } else {
      this.unstableFrames++;
      
      // 如果不稳定帧数超过阈值，才减少稳定帧数
      if (this.unstableFrames > this.maxUnstableFrames) {
        if (this.stableFrames > 0) {
          this.stableFrames--;
        }
        
        // 如果稳定帧数降至阈值以下，停止计时
        if (this.stableFrames < this.minStableFrames / 3) {
          this.isInPlank = false;
        }
      }
    }

    // 生成反馈
    const feedback = this.generatePlankFeedback(isCorrectForm, elbowsUnderShoulders);

    // 计算得分和正确性
    const score = isCorrectForm ? 80 : 60;
    // 平板支撑：只有姿势正确时才认为是正确的
    const isCorrect = isCorrectForm && this.stableFrames >= this.minStableFrames;

    return {
      isCorrect,
      score,
      feedback,
      duration: this.plankDuration / this.fps, // 转换为秒
    };
  }

  private generatePlankFeedback(isCorrectForm: boolean, elbowsUnderShoulders: boolean): string {
    if (!isCorrectForm) {
      if (!elbowsUnderShoulders) {
        return '肘部应在肩部下方';
      }
    }

    // 正确姿势反馈
    if (this.stableFrames < this.minStableFrames) {
      return `保持姿势稳定，还需 ${this.minStableFrames - this.stableFrames} 帧`;
    }

    const durationSeconds = this.plankDuration / this.fps;
    if (durationSeconds < 10) {
      return `姿势正确，已坚持 ${durationSeconds.toFixed(1)} 秒`;
    } else if (durationSeconds < 30) {
      return `做得好！已坚持 ${durationSeconds.toFixed(1)} 秒`;
    } else {
      return `太棒了！已坚持 ${durationSeconds.toFixed(1)} 秒`;
    }
  }

  reset(): void {
    this.plankDuration = 0;
    this.isInPlank = false;
    this.stableFrames = 0;
    this.unstableFrames = 0;
  }
}

/**
 * 开合跳分析器
 * 优化版本：添加完整动作跟踪和冷却机制
 */
export class JumpingJackAnalyzer {
  private jumpCount = 0;
  private lastState: 'closed' | 'open' = 'closed';
  private readonly armThreshold = 1.4; // 手臂张开比例阈值
  private readonly armHeightThreshold = 0.05; // 手臂抬高阈值
  
  // 状态稳定性跟踪
  private consecutiveOpenFrames = 0;   // 连续张开帧数
  private consecutiveClosedFrames = 0; // 连续闭合帧数
  private requiredFrames = 3;           // 所需帧数
  
  // 冷却机制
  private cooldownCounter = 0;
  private readonly cooldownFrames = 10; // 冷却时间
  
  // 完整动作跟踪
  private movementPhase: 'none' | 'opening' | 'closing' | 'complete' = 'none';
  private inOpenPosition = false; // 是否处于张开位置
  private lastArmRatio = 0.0;
  private readonly armRatioChangeThreshold = 0.5; // 手臂比例变化阈值

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftWrist = landmarks[15];
    const rightWrist = landmarks[16];
    
    // 检查可见性
    const shouldersVisible = leftShoulder?.visibility && leftShoulder.visibility >= 0.5 && 
                            rightShoulder?.visibility && rightShoulder.visibility >= 0.5;
    const wristsVisible = (leftWrist?.visibility && leftWrist.visibility >= 0.5) || 
                         (rightWrist?.visibility && rightWrist.visibility >= 0.5);

    if (!shouldersVisible || !wristsVisible || !leftShoulder || !rightShoulder || !leftWrist || !rightWrist) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保上半身在摄像头范围内',
        count: this.jumpCount,
      };
    }

    if (!leftShoulder || !rightShoulder || !leftWrist || !rightWrist) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保上半身在摄像头范围内',
        count: this.jumpCount,
      };
    }

    // 计算手臂的距离和角度
    const shoulderDistance = calculateDistance(leftShoulder, rightShoulder);
    const wristDistance = calculateDistance(leftWrist, rightWrist);

    // 计算手臂比例
    const armRatio = wristDistance / Math.max(shoulderDistance, 0.1); // 防止除零

    // 检查手臂高度 - 开合跳时手臂应该抬高（放宽条件：只要有一侧抬高即可）
    const leftArmRaised = leftWrist.y < leftShoulder.y - this.armHeightThreshold;
    const rightArmRaised = rightWrist.y < rightShoulder.y - this.armHeightThreshold;
    const armsRaised = leftArmRaised || rightArmRaised; // 改为 OR，只要一侧抬高即可

    // 放宽判断条件：手臂张开即可，不强制要求同时抬高（但抬高会提高得分）
    const armsOpen = armRatio > this.armThreshold;

    // 检查手臂比例变化的连续性，避免误检（放宽条件）
    const armRatioChange = Math.abs(armRatio - this.lastArmRatio);
    const isSmoothMovement = armRatioChange < this.armRatioChangeThreshold;
    this.lastArmRatio = armRatio;

    // 确定当前状态（放宽条件：只要手臂张开就认为是张开状态）
    let currentState: 'closed' | 'open' = 'closed';
    if (armsOpen) {
      // 如果手臂张开，即使变化较大也认为是张开状态
      currentState = 'open';
    }

    // 更新连续帧计数
    if (currentState === 'open') {
      this.consecutiveOpenFrames++;
      this.consecutiveClosedFrames = 0;
    } else if (currentState === 'closed') {
      this.consecutiveClosedFrames++;
      this.consecutiveOpenFrames = 0;
    }

    // 状态判断 - 需要更多帧数才确认状态
    const previousState = this.lastState;
    let confirmedState = this.lastState;

    if (this.consecutiveOpenFrames >= this.requiredFrames) {
      confirmedState = 'open';
    } else if (this.consecutiveClosedFrames >= this.requiredFrames) {
      confirmedState = 'closed';
    }

    // 冷却计数器处理
    if (this.cooldownCounter > 0) {
      this.cooldownCounter--;
    }

    // 完整动作跟踪和计数逻辑
    const countUpdated = this.updateJumpingJackCount(previousState, confirmedState);

    this.lastState = confirmedState;

    // 生成反馈
    const feedback = this.generateJumpingJackFeedback(confirmedState, armsOpen, armsRaised);

    // 计算得分和正确性
    const score = this.calculateJumpingJackScore(confirmedState, armsOpen, armsRaised, armRatio);
    // 开合跳：放宽正确性判断（只要手臂张开就认为正确，完成完整动作更佳）
    const isCorrect = this.movementPhase === 'complete' || 
                     (confirmedState === 'open' && armsOpen) ||
                     (armsOpen && armsRaised); // 即使不在确认状态，只要张开且抬高也算正确

    return {
      isCorrect,
      score,
      feedback,
      count: Math.floor(this.jumpCount / 2), // 除以2并向下取整显示
    };
  }

  private updateJumpingJackCount(previousState: 'closed' | 'open', currentState: 'closed' | 'open'): boolean {
    let countUpdated = false;

    // 状态变化检测
    if (previousState !== currentState) {
      // 状态变化：闭合 -> 张开
      if (previousState === 'closed' && currentState === 'open') {
        if (this.movementPhase === 'none' || this.movementPhase === 'complete') {
          this.movementPhase = 'opening';
          this.inOpenPosition = true;
        }
      }
      // 状态变化：张开 -> 闭合
      else if (previousState === 'open' && currentState === 'closed') {
        if (this.movementPhase === 'opening' && this.inOpenPosition) {
          this.movementPhase = 'closing';
          this.inOpenPosition = false;

          // 完成一次完整的开合跳动作
          if (this.cooldownCounter === 0) {
            this.jumpCount++;
            countUpdated = true;
            this.cooldownCounter = this.cooldownFrames;
            this.movementPhase = 'complete';
          }
        }
      }
    }

    return countUpdated;
  }

  private generateJumpingJackFeedback(state: 'closed' | 'open', armsOpen: boolean, armsRaised: boolean): string {
    if (state === 'open') {
      if (this.movementPhase === 'opening') {
        return '很好！手臂张开，准备合拢';
      } else {
        return '保持手臂张开姿势';
      }
    } else { // closed
      if (this.movementPhase === 'closing') {
        return '很好！完成一次开合跳';
      } else if (this.movementPhase === 'complete') {
        return '准备下一次开合跳';
      } else {
        // 给出具体的改进建议
        if (!armsRaised) {
          return '请将手臂抬高到肩部以上';
        } else {
          return '请跳起并张开手臂';
        }
      }
    }
  }

  private calculateJumpingJackScore(
    state: 'closed' | 'open',
    armsOpen: boolean,
    armsRaised: boolean,
    armRatio: number
  ): number {
    const baseScore = 60;

    if (state === 'open') {
      // 张开状态的得分
      if (armsOpen && armsRaised) {
        return 90; // 完美张开
      } else if (armsRaised) {
        return 75; // 手臂抬高但未完全张开
      } else {
        return baseScore;
      }
    } else {
      // 闭合状态的得分
      if (this.movementPhase === 'complete') {
        return 85; // 完成了完整动作
      } else if (this.movementPhase === 'closing') {
        return 80; // 正在闭合
      } else {
        return baseScore;
      }
    }
  }

  reset(): void {
    this.jumpCount = 0;
    this.lastState = 'closed';
    this.consecutiveOpenFrames = 0;
    this.consecutiveClosedFrames = 0;
    this.cooldownCounter = 0;
    this.movementPhase = 'none';
    this.inOpenPosition = false;
    this.lastArmRatio = 0.0;
  }
}

/**
 * 创建对应运动类型的分析器
 */
export function createAnalyzer(exerciseType: string) {
  switch (exerciseType) {
    case 'squat':
      return new SquatAnalyzer();
    case 'pushup':
      return new PushupAnalyzer();
    case 'plank':
      return new PlankAnalyzer();
    case 'jumping_jack':
      return new JumpingJackAnalyzer();
    default:
      return new SquatAnalyzer();
  }
}

