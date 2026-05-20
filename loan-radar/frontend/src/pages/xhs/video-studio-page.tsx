import {
  DeleteOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ScissorOutlined,
  UploadOutlined,
  VideoCameraOutlined,
  RobotOutlined,
  PictureOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Image,
  Input,
  InputNumber,
  Row,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
} from "antd";
import { useEffect, useState } from "react";

import { PageHeader } from "../../components/AppShell";
import {
  deleteVideoFile,
  describeVideoWithAi,
  extractVideoCover,
  fetchVideoFiles,
  uploadAssetFile,
} from "../../api/xhs-api";
import { formatShanghaiTime } from "../../lib/time";
import type { VideoFile } from "../../api/xhs-api";

const { Text, Paragraph } = Typography;

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number): string {
  if (seconds <= 0) return "--:--";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function XhsVideoStudioPage() {
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [totalVideos, setTotalVideos] = useState(0);
  const [videoPage, setVideoPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [coverVideo, setCoverVideo] = useState<string>("");
  const [coverTimestamp, setCoverTimestamp] = useState(0);
  const [coverWidth, setCoverWidth] = useState(1080);
  const [coverHeight, setCoverHeight] = useState(1440);
  const [isExtracting, setIsExtracting] = useState(false);
  const [coverResult, setCoverResult] = useState<{ download_url: string; width: number; height: number } | null>(null);

  const [describeUrl, setDescribeUrl] = useState("");
  const [describeInstruction, setDescribeInstruction] = useState("");
  const [isDescribing, setIsDescribing] = useState(false);
  const [describeResult, setDescribeResult] = useState<string | null>(null);

  async function loadVideos() {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchVideoFiles(videoPage, 20);
      setVideos(result.items);
      setTotalVideos(result.total);
    } catch {
      setError("视频列表加载失败。");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadVideos();
  }, [videoPage]);

  async function handleUploadVideo(file: File) {
    try {
      await uploadAssetFile(file);
      setMessage("视频上传成功。");
      void loadVideos();
    } catch {
      setError("视频上传失败。");
    }
    return false;
  }

  async function handleDeleteVideo(fileName: string) {
    try {
      await deleteVideoFile(fileName);
      setVideos((prev) => prev.filter((v) => v.file_name !== fileName));
      setMessage("视频已删除。");
    } catch {
      setError("删除视频失败。");
    }
  }

  async function handleExtractCover() {
    if (!coverVideo) {
      setError("请选择或输入视频文件名。");
      return;
    }
    setIsExtracting(true);
    setError(null);
    setMessage(null);
    setCoverResult(null);
    try {
      const result = await extractVideoCover({
        video_file_name: coverVideo,
        timestamp_seconds: coverTimestamp,
        width: coverWidth,
        height: coverHeight,
      });
      setCoverResult({ download_url: result.download_url, width: result.width, height: result.height });
      setMessage("封面提取成功。");
    } catch {
      setError("封面提取失败，请确认已安装 ffmpeg 且视频文件有效。");
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleDescribe() {
    if (!describeUrl.trim()) {
      setError("请输入视频 URL。");
      return;
    }
    setIsDescribing(true);
    setError(null);
    setMessage(null);
    setDescribeResult(null);
    try {
      const result = await describeVideoWithAi({
        video_url: describeUrl.trim(),
        instruction: describeInstruction.trim() || undefined,
      });
      setDescribeResult(result.text);
      setMessage("视频描述生成成功。");
    } catch {
      setError("视频描述失败，请确认已配置多模态模型。");
    } finally {
      setIsDescribing(false);
    }
  }

  function selectVideoForCover(fileName: string) {
    setCoverVideo(fileName);
  }

  function selectVideoForDescribe(fileName: string) {
    setDescribeUrl(`/api/files/media/${fileName}`);
  }

  return (
    <div>
      <PageHeader
        eyebrow="XHS Video Studio"
        title="视频工坊"
        description="视频上传管理、封面提取、AI 视频描述，赋能小红书视频内容创作。"
        action={
          <Button icon={<ReloadOutlined />} onClick={loadVideos} loading={isLoading}>
            刷新
          </Button>
        }
      />

      {error && (
        <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} style={{ marginBottom: 16 }} />
      )}
      {message && (
        <Alert type="success" message={message} showIcon closable onClose={() => setMessage(null)} style={{ marginBottom: 16 }} />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={14}>
          <Card
            title={
              <Space>
                <ScissorOutlined /> 封面提取
              </Space>
            }
            extra={
              <Text type="secondary" style={{ fontSize: 11 }}>
                需安装 ffmpeg
              </Text>
            }
          >
            <Space direction="vertical" style={{ width: "100%" }} size={12}>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                  视频文件名
                </Text>
                <Space.Compact style={{ width: "100%" }}>
                  <Input
                    value={coverVideo}
                    onChange={(e) => setCoverVideo(e.target.value)}
                    placeholder="从下方视频列表选择，或手动输入文件名"
                  />
                </Space.Compact>
              </div>

              <Row gutter={12}>
                <Col span={8}>
                  <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                    时间点（秒）
                  </Text>
                  <InputNumber
                    value={coverTimestamp}
                    onChange={(v) => setCoverTimestamp(v ?? 0)}
                    min={0}
                    step={0.5}
                    style={{ width: "100%" }}
                  />
                </Col>
                <Col span={8}>
                  <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                    宽度
                  </Text>
                  <InputNumber
                    value={coverWidth}
                    onChange={(v) => setCoverWidth(v ?? 1080)}
                    min={128}
                    max={3840}
                    style={{ width: "100%" }}
                  />
                </Col>
                <Col span={8}>
                  <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                    高度
                  </Text>
                  <InputNumber
                    value={coverHeight}
                    onChange={(v) => setCoverHeight(v ?? 1440)}
                    min={128}
                    max={3840}
                    style={{ width: "100%" }}
                  />
                </Col>
              </Row>

              <Row justify="end">
                <Space>
                  <Button
                    onClick={() => {
                      setCoverVideo("");
                      setCoverTimestamp(0);
                      setCoverWidth(1080);
                      setCoverHeight(1440);
                      setCoverResult(null);
                    }}
                    disabled={isExtracting}
                  >
                    重置
                  </Button>
                  <Button
                    type="primary"
                    icon={<ScissorOutlined />}
                    onClick={handleExtractCover}
                    loading={isExtracting}
                  >
                    提取封面
                  </Button>
                </Space>
              </Row>

              {coverResult && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12, marginBottom: 6, display: "block" }}>
                    提取结果 ({coverResult.width}×{coverResult.height})
                  </Text>
                  <div
                    style={{
                      background: "#F5F7FA",
                      borderRadius: 6,
                      padding: 8,
                      textAlign: "center",
                    }}
                  >
                    <Image
                      src={coverResult.download_url}
                      alt="cover"
                      style={{ maxHeight: 240, objectFit: "contain" }}
                    />
                  </div>
                </div>
              )}
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={10}>
          <Card
            title={
              <Space>
                <RobotOutlined /> AI 视频描述
              </Space>
            }
            extra={
              <Text type="secondary" style={{ fontSize: 11 }}>
                需配置多模态模型
              </Text>
            }
          >
            <Space direction="vertical" style={{ width: "100%" }} size={12}>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                  视频 URL
                </Text>
                <Input
                  value={describeUrl}
                  onChange={(e) => setDescribeUrl(e.target.value)}
                  placeholder="从下方视频列表选择，或输入视频 URL"
                  disabled={isDescribing}
                />
              </div>

              <div>
                <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                  自定义指令（可选）
                </Text>
                <Input
                  value={describeInstruction}
                  onChange={(e) => setDescribeInstruction(e.target.value)}
                  placeholder="如：提炼视频卖点、分析目标受众..."
                  disabled={isDescribing}
                />
              </div>

              <Button
                onClick={handleDescribe}
                loading={isDescribing}
                block
                icon={<RobotOutlined />}
              >
                生成描述
              </Button>

              {describeResult && (
                <Paragraph
                  style={{
                    background: "#F5F7FA",
                    padding: 12,
                    borderRadius: 6,
                    fontSize: 13,
                    margin: 0,
                  }}
                >
                  {describeResult}
                </Paragraph>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="videos"
        items={[
          {
            key: "videos",
            label: (
              <Space>
                <VideoCameraOutlined /> 视频资产
              </Space>
            ),
            children: (
              <>
                <div style={{ marginBottom: 16 }}>
                  <Upload
                    accept="video/*,.mp4,.mov,.avi,.mkv"
                    showUploadList={false}
                    beforeUpload={(file) => {
                      void handleUploadVideo(file);
                      return false;
                    }}
                  >
                    <Button icon={<UploadOutlined />}>上传视频</Button>
                  </Upload>
                  <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                    支持 MP4、MOV、AVI、MKV，最大 100MB
                  </Text>
                </div>

                {isLoading ? (
                  <div style={{ textAlign: "center", padding: 48 }}>
                    <Spin tip="正在加载视频..." />
                  </div>
                ) : videos.length === 0 ? (
                  <Empty
                    image={<VideoCameraOutlined style={{ fontSize: 48, color: "#8c8c8c" }} />}
                    imageStyle={{ height: 60 }}
                    description="暂无视频资产，上传视频后将显示在这里。"
                    style={{ padding: 32 }}
                  />
                ) : (
                  <Table
                    dataSource={videos}
                    rowKey="file_name"
                    pagination={{
                      current: videoPage,
                      pageSize: 20,
                      total: totalVideos,
                      onChange: (p) => setVideoPage(p),
                      showSizeChanger: false,
                      size: "small",
                    }}
                    size="small"
                    columns={[
                      {
                        title: "文件",
                        dataIndex: "file_name",
                        key: "file_name",
                        ellipsis: true,
                        render: (name: string) => (
                          <Space>
                            <VideoCameraOutlined />
                            <Text ellipsis style={{ maxWidth: 260 }}>{name}</Text>
                          </Space>
                        ),
                      },
                      {
                        title: "大小",
                        dataIndex: "size",
                        key: "size",
                        width: 100,
                        render: (v: number) => formatFileSize(v),
                      },
                      {
                        title: "时长",
                        dataIndex: "duration",
                        key: "duration",
                        width: 80,
                        render: (v: number) => (
                          <Tag>{formatDuration(v)}</Tag>
                        ),
                      },
                      {
                        title: "类型",
                        dataIndex: "media_type",
                        key: "media_type",
                        width: 110,
                        render: (v: string) => <Tag>{v}</Tag>,
                      },
                      {
                        title: "操作",
                        key: "actions",
                        width: 260,
                        render: (_: unknown, record: VideoFile) => (
                          <Space size={4}>
                            <Button
                              size="small"
                              icon={<PlayCircleOutlined />}
                              onClick={() => window.open(record.url, "_blank")}
                            >
                              播放
                            </Button>
                            <Button
                              size="small"
                              icon={<ScissorOutlined />}
                              onClick={() => selectVideoForCover(record.file_name)}
                            >
                              提取封面
                            </Button>
                            <Button
                              size="small"
                              icon={<RobotOutlined />}
                              onClick={() => selectVideoForDescribe(record.file_name)}
                            >
                              AI 描述
                            </Button>
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleDeleteVideo(record.file_name)}
                            />
                          </Space>
                        ),
                      },
                    ]}
                  />
                )}
              </>
            ),
          },
          {
            key: "covers",
            label: (
              <Space>
                <PictureOutlined /> 已提取封面
              </Space>
            ),
            children: (
              <Empty
                image={<PictureOutlined style={{ fontSize: 48, color: "#8c8c8c" }} />}
                imageStyle={{ height: 60 }}
                description="提取的封面将显示在这里，可在图片工坊中查看和管理。"
                style={{ padding: 32 }}
              />
            ),
          },
        ]}
      />
    </div>
  );
}
