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
 */
export function calculateAngle(
  point1: Landmark,
  point2: Landmark,
  point3: Landmark
): number {
  const radians =
    Math.atan2(point3.y - point2.y, point3.x - point2.x) -
    Math.atan2(point1.y - point2.y, point1.x - point2.x);
  let angle = Math.abs((radians * 180.0) / Math.PI);
  if (angle > 180.0) {
    angle = 360 - angle;
  }
  return angle;
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
 */
export class SquatAnalyzer {
  private squatCount = 0;
  private inSquatPosition = false;
  private previousKneeAngle = 180;
  private readonly SQUAT_THRESHOLD = 90; // 深蹲角度阈值
  private readonly STANDING_THRESHOLD = 160; // 站立角度阈值

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    // MediaPipe Pose 关键点索引
    // 左腿: 23(hip) -> 25(knee) -> 27(ankle)
    // 右腿: 24(hip) -> 26(knee) -> 28(ankle)
    const leftHip = landmarks[23];
    const leftKnee = landmarks[25];
    const leftAnkle = landmarks[27];
    const rightHip = landmarks[24];
    const rightKnee = landmarks[26];
    const rightAnkle = landmarks[28];

    if (
      !leftHip ||
      !leftKnee ||
      !leftAnkle ||
      !rightHip ||
      !rightKnee ||
      !rightAnkle
    ) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保全身在画面中',
      };
    }

    // 计算左右膝盖角度
    const leftKneeAngle = calculateAngle(leftHip, leftKnee, leftAnkle);
    const rightKneeAngle = calculateAngle(rightHip, rightKnee, rightAnkle);
    const avgKneeAngle = (leftKneeAngle + rightKneeAngle) / 2;

    // 检测深蹲动作
    let isCorrect = true;
    let feedback = '准备开始深蹲';
    let score = 50;

    // 检测下蹲（角度减小）
    if (avgKneeAngle < this.SQUAT_THRESHOLD) {
      if (!this.inSquatPosition) {
        // 刚进入深蹲位置
        this.inSquatPosition = true;
        feedback = '很好！保持深蹲姿势';
        score = 80;
      } else {
        // 在深蹲位置
        feedback = '保持深蹲姿势';
        score = 85;
      }
    } else if (avgKneeAngle > this.STANDING_THRESHOLD) {
      // 站立位置
      if (this.inSquatPosition) {
        // 从深蹲站起，完成一次
        this.squatCount++;
        this.inSquatPosition = false;
        feedback = `完成！已做 ${this.squatCount} 次深蹲`;
        score = 100;
      } else {
        feedback = '准备下蹲';
        score = 60;
      }
    } else {
      // 中间位置
      if (this.inSquatPosition) {
        feedback = '正在站起，保持动作标准';
        score = 75;
      } else {
        feedback = '可以蹲得更低一些';
        isCorrect = false;
        score = 40;
      }
    }

    // 检查姿态正确性
    const hipDistance = calculateDistance(leftHip, rightHip);
    const ankleDistance = calculateDistance(leftAnkle, rightAnkle);
    const balanceRatio = Math.abs(hipDistance - ankleDistance) / hipDistance;

    if (balanceRatio > 0.3) {
      feedback += '，注意保持平衡';
      score = Math.max(0, score - 10);
    }

    this.previousKneeAngle = avgKneeAngle;

    return {
      isCorrect,
      score: Math.min(100, Math.max(0, score)),
      feedback,
      count: this.squatCount,
    };
  }

  reset(): void {
    this.squatCount = 0;
    this.inSquatPosition = false;
    this.previousKneeAngle = 180;
  }
}

/**
 * 俯卧撑分析器
 */
export class PushupAnalyzer {
  private pushupCount = 0;
  private inDownPosition = false;
  private readonly DOWN_THRESHOLD = 90; // 下压角度阈值
  private readonly UP_THRESHOLD = 160; // 上推角度阈值

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    // MediaPipe Pose 关键点索引
    // 左臂: 11(shoulder) -> 13(elbow) -> 15(wrist)
    // 右臂: 12(shoulder) -> 14(elbow) -> 16(wrist)
    const leftShoulder = landmarks[11];
    const leftElbow = landmarks[13];
    const leftWrist = landmarks[15];
    const rightShoulder = landmarks[12];
    const rightElbow = landmarks[14];
    const rightWrist = landmarks[16];

    if (
      !leftShoulder ||
      !leftElbow ||
      !leftWrist ||
      !rightShoulder ||
      !rightElbow ||
      !rightWrist
    ) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保全身在画面中',
      };
    }

    // 计算左右手臂角度
    const leftArmAngle = calculateAngle(leftShoulder, leftElbow, leftWrist);
    const rightArmAngle = calculateAngle(rightShoulder, rightElbow, rightWrist);
    const avgArmAngle = (leftArmAngle + rightArmAngle) / 2;

    let isCorrect = true;
    let feedback = '准备开始俯卧撑';
    let score = 50;

    // 检测下压（角度减小）
    if (avgArmAngle < this.DOWN_THRESHOLD) {
      if (!this.inDownPosition) {
        this.inDownPosition = true;
        feedback = '很好！下压到位';
        score = 85;
      } else {
        feedback = '保持下压姿势';
        score = 80;
      }
    } else if (avgArmAngle > this.UP_THRESHOLD) {
      // 上推位置
      if (this.inDownPosition) {
        // 从下压推起，完成一次
        this.pushupCount++;
        this.inDownPosition = false;
        feedback = `完成！已做 ${this.pushupCount} 次俯卧撑`;
        score = 100;
      } else {
        feedback = '准备下压';
        score = 60;
      }
    } else {
      // 中间位置
      if (this.inDownPosition) {
        feedback = '正在上推，保持身体挺直';
        score = 75;
      } else {
        feedback = '可以压得更低一些';
        isCorrect = false;
        score = 40;
      }
    }

    // 检查身体是否保持直线（检查肩膀和臀部是否水平）
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];
    const leftShoulderY = leftShoulder.y;
    const rightShoulderY = rightShoulder.y;
    const avgHipY = leftHip && rightHip ? (leftHip.y + rightHip.y) / 2 : 0;
    const avgShoulderY = (leftShoulderY + rightShoulderY) / 2;

    if (avgHipY > 0 && avgShoulderY > 0) {
      const bodyAlignment = Math.abs(avgShoulderY - avgHipY);
      if (bodyAlignment > 0.15) {
        feedback += '，注意保持身体一条直线';
        score = Math.max(0, score - 15);
      }
    }

    return {
      isCorrect,
      score: Math.min(100, Math.max(0, score)),
      feedback,
      count: this.pushupCount,
    };
  }

  reset(): void {
    this.pushupCount = 0;
    this.inDownPosition = false;
  }
}

/**
 * 平板支撑分析器
 */
export class PlankAnalyzer {
  private startTime: number | null = null;
  private holdDuration = 0;
  private readonly MIN_HOLD_TIME = 1000; // 最小保持时间（毫秒）

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];
    const leftKnee = landmarks[25];
    const rightKnee = landmarks[26];
    const leftAnkle = landmarks[27];
    const rightAnkle = landmarks[28];

    if (
      !leftShoulder ||
      !rightShoulder ||
      !leftHip ||
      !rightHip ||
      !leftKnee ||
      !rightKnee ||
      !leftAnkle ||
      !rightAnkle
    ) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保全身在画面中',
        duration: 0,
      };
    }

    // 计算身体各部位的平均 Y 坐标
    const avgShoulderY = (leftShoulder.y + rightShoulder.y) / 2;
    const avgHipY = (leftHip.y + rightHip.y) / 2;
    const avgKneeY = (leftKnee.y + rightKnee.y) / 2;
    const avgAnkleY = (leftAnkle.y + rightAnkle.y) / 2;

    // 检查身体是否保持直线（肩膀、臀部、膝盖、脚踝应该在一条线上）
    const bodyAlignment =
      Math.abs(avgShoulderY - avgHipY) +
      Math.abs(avgHipY - avgKneeY) +
      Math.abs(avgKneeY - avgAnkleY);
    const alignmentScore = bodyAlignment / 3;

    let isCorrect = true;
    let feedback = '准备开始平板支撑';
    let score = 50;

    // 判断是否在正确的平板支撑姿势
    if (alignmentScore < 0.05) {
      // 身体保持直线
      if (this.startTime === null) {
        this.startTime = Date.now();
      }
      this.holdDuration = Math.floor((Date.now() - this.startTime) / 1000);

      feedback = `很好！保持姿势，已坚持 ${this.holdDuration} 秒`;
      score = 90;
    } else if (alignmentScore < 0.1) {
      // 轻微偏差
      if (this.startTime === null) {
        this.startTime = Date.now();
      }
      this.holdDuration = Math.floor((Date.now() - this.startTime) / 1000);

      feedback = `保持核心收紧，已坚持 ${this.holdDuration} 秒`;
      score = 75;
    } else {
      // 姿势不正确
      if (avgHipY > avgShoulderY + 0.1) {
        feedback = '臀部太高，请降低臀部';
      } else if (avgHipY < avgShoulderY - 0.1) {
        feedback = '臀部太低，请抬高臀部';
      } else {
        feedback = '请保持身体一条直线';
      }
      isCorrect = false;
      score = 40;
      // 姿势不正确时重置计时
      if (this.startTime !== null && this.holdDuration < 2) {
        this.startTime = null;
        this.holdDuration = 0;
      }
    }

    return {
      isCorrect,
      score: Math.min(100, Math.max(0, score)),
      feedback,
      duration: this.holdDuration,
    };
  }

  reset(): void {
    this.startTime = null;
    this.holdDuration = 0;
  }
}

/**
 * 开合跳分析器
 */
export class JumpingJackAnalyzer {
  private jumpCount = 0;
  private previousArmDistance = 0;
  private previousLegDistance = 0;
  private inJumpPosition = false;
  private readonly ARM_THRESHOLD = 0.3; // 手臂距离阈值
  private readonly LEG_THRESHOLD = 0.25; // 腿部距离阈值

  analyze(landmarks: Landmark[]): ExerciseAnalysis {
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftWrist = landmarks[15];
    const rightWrist = landmarks[16];
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];
    const leftAnkle = landmarks[27];
    const rightAnkle = landmarks[28];

    if (
      !leftShoulder ||
      !rightShoulder ||
      !leftWrist ||
      !rightWrist ||
      !leftHip ||
      !rightHip ||
      !leftAnkle ||
      !rightAnkle
    ) {
      return {
        isCorrect: false,
        score: 0,
        feedback: '请确保全身在画面中',
      };
    }

    // 计算手臂和腿部的距离
    const armDistance = calculateDistance(leftWrist, rightWrist);
    const legDistance = calculateDistance(leftAnkle, rightAnkle);
    const shoulderDistance = calculateDistance(leftShoulder, rightShoulder);
    const hipDistance = calculateDistance(leftHip, rightHip);

    // 归一化距离（相对于肩膀/臀部距离）
    const normalizedArmDistance = armDistance / shoulderDistance;
    const normalizedLegDistance = legDistance / hipDistance;

    let isCorrect = true;
    let feedback = '准备开始开合跳';
    let score = 50;

    // 检测开合动作
    const armsOpen = normalizedArmDistance > this.ARM_THRESHOLD;
    const legsOpen = normalizedLegDistance > this.LEG_THRESHOLD;

    if (armsOpen && legsOpen) {
      // 打开状态
      if (!this.inJumpPosition) {
        // 刚进入打开状态
        this.inJumpPosition = true;
        feedback = '很好！保持打开姿势';
        score = 80;
      } else {
        feedback = '保持打开姿势';
        score = 75;
      }
    } else if (!armsOpen && !legsOpen) {
      // 闭合状态
      if (this.inJumpPosition) {
        // 从打开到闭合，完成一次
        this.jumpCount++;
        this.inJumpPosition = false;
        feedback = `完成！已做 ${this.jumpCount} 次开合跳`;
        score = 100;
      } else {
        feedback = '准备跳起';
        score = 60;
      }
    } else {
      // 部分打开
      if (this.inJumpPosition) {
        feedback = '正在闭合，保持节奏';
        score = 70;
      } else {
        feedback = '手臂和腿部需要同时打开';
        isCorrect = false;
        score = 40;
      }
    }

    this.previousArmDistance = normalizedArmDistance;
    this.previousLegDistance = normalizedLegDistance;

    return {
      isCorrect,
      score: Math.min(100, Math.max(0, score)),
      feedback,
      count: this.jumpCount,
    };
  }

  reset(): void {
    this.jumpCount = 0;
    this.previousArmDistance = 0;
    this.previousLegDistance = 0;
    this.inJumpPosition = false;
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

