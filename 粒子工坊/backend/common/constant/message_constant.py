"""提示文案常量：集中管理返回给前端的错误 / 成功提示，禁止在 service / controller 里写死中文。"""


class MessageConstant:
    # —— 通用 ——
    PARAM_INVALID = "请求参数不合法"

    # —— 大模型 ——
    LLM_NOT_CONFIGURED = "未配置大模型 API Key，请先到「设置」页填写"
    LLM_SETTINGS_SAVED = "模型设置已保存"

    # —— 生成任务 ——
    RUN_NOT_FOUND = "任务不存在"
    RUN_NOT_WAITING_REVIEW = "任务当前不在待审核状态，无法继续"
    RUN_NOT_RUNNING = "任务当前不在运行中，无法取消"
    RUN_VARIANT_NOT_FOUND = "所选变体不存在或没有可用的出图结果"
    RUN_FEEDBACK_REQUIRED = "打回时请填写修改意见"
    RUN_VARIANT_REQUIRED = "请选择一个变体"
    RUN_EDITED_ART_INVALID = "手改后的像素数据不合法"
    RUN_CANCELLED = "任务已取消"

    # —— 选项 ——
    OPTION_INVALID = "按钮选项不合法"

    # —— 取色 ——
    EXTRACT_FILE_EMPTY = "请上传图片文件"
    EXTRACT_FILE_TOO_LARGE = "图片文件过大"
    EXTRACT_IMAGE_TOO_LARGE = "图片尺寸超出上限"
    EXTRACT_IMAGE_INVALID = "无法识别的图片文件"

    # —— 粒子库 ——
    PARTICLE_NOT_FOUND = "粒子不存在"
    PARTICLE_NAME_INVALID = "粒子名只能包含英文字母、数字、下划线和短横线"
    PARTICLE_NAME_EXISTS = "粒子库中已有同名粒子"
    SHOWCASE_REBUILT = "总览图已重建"
