import { CloudDownloadOutlined, LinkOutlined, StarOutlined } from "@ant-design/icons";
import { Button, Card, Col, Drawer, Row, Space, Table, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { convertPostsToNotes, getLeads, getPosts, type Lead, type Post, type PostQueryParams } from "../api";
import { showToast } from "../components/ToastContainer";

const { Text, Paragraph } = Typography;

const PLATFORM_LABELS: Record<string, string> = { xhs: "小红书", douyin: "抖音", zhihu: "知乎" };
const SOURCE_TYPE_LABELS: Record<string, string> = {
  keyword: "关键词",
  competitor_account: "同行账号",
  manual_post: "手动添加",
  hot_post_rule: "爆款规则",
  xhs_library: "内容库",
  crawl_task: "采集任务",
};

const LEAD_LEVEL_COLORS: Record<string, string> = { A: "red", B: "blue", C: "orange", D: "default" };

function InteractCell({ value }: { value: number }) {
  return (
    <span style={{ fontSize: 12, color: value > 0 ? "#374151" : "#d9d9d9" }}>
      {value > 0 ? value : "-"}
    </span>
  );
}

function HotBadge({ isHot }: { isHot: boolean }) {
  if (!isHot) return <Text type="secondary" style={{ fontSize: 12 }}>-</Text>;
  return <Tag color="red" style={{ margin: 0, fontSize: 11 }}>爆款</Tag>;
}

function LeadCountLink({ count, postId }: { count: number; postId: number }) {
  const navigate = useNavigate();
  if (count <= 0) return <Text type="secondary" style={{ fontSize: 12 }}>0</Text>;
  return (
    <Button
      type="link"
      size="small"
      style={{ padding: 0, fontSize: 13, fontWeight: 600, color: "#2F54EB" }}
      onClick={(e) => {
        e.stopPropagation();
        navigate(`/leads?source_post_id=${postId}`);
      }}
    >
      {count}
    </Button>
  );
}

export default function PostPoolPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight");

  const [items, setItems] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);

  const [filters, setFilters] = useState<PostQueryParams>(() => ({
    platform: searchParams.get("platform") || "",
    source_type: searchParams.get("source_type") || "",
    keyword: searchParams.get("keyword") || "",
    is_hot: searchParams.get("is_hot") === "true" ? true : undefined,
  }));

  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [converting, setConverting] = useState(false);

  const [detailPost, setDetailPost] = useState<Post | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLeads, setDetailLeads] = useState<Lead[]>([]);
  const [detailLeadsLoading, setDetailLeadsLoading] = useState(false);

  const [statTotals, setStatTotals] = useState({ all: 0, hot: 0, withLeads: 0 });

  async function loadData(nextPage = page, nextPageSize = pageSize, nextFilters = filters) {
    setLoading(true);
    try {
      const apiParams: PostQueryParams = {
        platform: nextFilters.platform || undefined,
        source_type: nextFilters.source_type || undefined,
        keyword: nextFilters.keyword || undefined,
        is_hot: nextFilters.is_hot,
        page: nextPage,
        page_size: nextPageSize,
      };
      const result = await getPosts(apiParams);
      setItems(result.items);
      setTotal(result.total);
      setPage(result.page);

      const allResult = await getPosts({ ...apiParams, page: 1, page_size: 1 });
      const hotResult = await getPosts({ ...apiParams, is_hot: true, page: 1, page_size: 1 });
      setStatTotals({
        all: allResult.total,
        hot: hotResult.total,
        withLeads: result.items.filter((p) => p.lead_count > 0).length,
      });
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载帖子失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(1, pageSize, filters);
  }, []);

  async function handleSearch() {
    setPage(1);
    setSelectedRowKeys([]);
    await loadData(1, pageSize, filters);
  }

  async function handleReset() {
    const resetFilters: PostQueryParams = { platform: "", source_type: "", keyword: "" };
    setFilters(resetFilters);
    setPage(1);
    setSelectedRowKeys([]);
    await loadData(1, pageSize, resetFilters);
  }

  async function handleViewDetail(post: Post) {
    setDetailPost(post);
    setDetailOpen(true);
    setDetailLeadsLoading(true);
    try {
      const result = await getLeads({ source_post_id: post.id, page: 1, page_size: 50 });
      setDetailLeads(result.items);
    } catch {
      setDetailLeads([]);
    } finally {
      setDetailLeadsLoading(false);
    }
  }

  async function handleSaveToLibrary() {
    if (selectedRowKeys.length === 0) return;
    setConverting(true);
    try {
      const result = await convertPostsToNotes({ post_ids: selectedRowKeys.map(Number) });
      showToast(
        "success",
        "收藏到内容库完成",
        `成功 ${result.converted_count} 条，跳过 ${result.skipped_count} 条，失败 ${result.failed_count} 条`,
      );
      setSelectedRowKeys([]);
    } catch (err) {
      showToast("error", "收藏到内容库失败", err instanceof Error ? err.message : "未知错误");
    } finally {
      setConverting(false);
    }
  }

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      width: 60,
      render: (id: number) => <Text style={{ fontSize: 12, color: "#8c8c8c" }}>{id}</Text>,
    },
    {
      title: "平台",
      dataIndex: "platform",
      width: 80,
      render: (p: string) => <Tag style={{ margin: 0, fontSize: 12 }}>{PLATFORM_LABELS[p] || p}</Tag>,
    },
    {
      title: "来源",
      dataIndex: "source_type",
      width: 90,
      render: (st: string) => <Text style={{ fontSize: 12 }}>{SOURCE_TYPE_LABELS[st] || st}</Text>,
    },
    {
      title: "标题/内容",
      dataIndex: "title",
      ellipsis: true,
      render: (title: string, record: Post) => (
        <Text ellipsis style={{ maxWidth: 300, fontSize: 13 }}>
          {title || record.content || "-"}
        </Text>
      ),
    },
    {
      title: "作者",
      dataIndex: "author_name",
      width: 100,
      render: (name: string) => <Text style={{ fontSize: 12 }}>{name || "-"}</Text>,
    },
    {
      title: "点赞",
      dataIndex: "like_count",
      width: 64,
      sorter: (a: Post, b: Post) => a.like_count - b.like_count,
      render: (v: number) => <InteractCell value={v} />,
    },
    {
      title: "评论",
      dataIndex: "comment_count",
      width: 64,
      sorter: (a: Post, b: Post) => a.comment_count - b.comment_count,
      render: (v: number) => <InteractCell value={v} />,
    },
    {
      title: "收藏",
      dataIndex: "collect_count",
      width: 64,
      sorter: (a: Post, b: Post) => a.collect_count - b.collect_count,
      render: (v: number) => <InteractCell value={v} />,
    },
    {
      title: "爆款",
      dataIndex: "is_hot",
      width: 64,
      render: (isHot: boolean) => <HotBadge isHot={isHot} />,
    },
    {
      title: "线索",
      dataIndex: "lead_count",
      width: 64,
      sorter: (a: Post, b: Post) => a.lead_count - b.lead_count,
      render: (count: number, record: Post) => <LeadCountLink count={count} postId={record.id} />,
    },
    {
      title: "发布时间",
      dataIndex: "publish_time",
      width: 110,
      sorter: (a: Post, b: Post) => new Date(a.publish_time || "").getTime() - new Date(b.publish_time || "").getTime(),
      render: (v: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {v ? dayjs(v).format("MM-DD HH:mm") : "-"}
        </Text>
      ),
    },
    {
      title: "操作",
      width: 100,
      render: (_: unknown, record: Post) => (
        <Space size={4}>
          <Button type="link" size="small" style={{ padding: 0, fontSize: 12 }} onClick={() => handleViewDetail(record)}>
            详情
          </Button>
          {record.post_url && (
            <a href={record.post_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
              原文
            </a>
          )}
        </Space>
      ),
    },
  ];

  const statCards = [
    { label: "全部帖子", value: statTotals.all, color: undefined as string | undefined },
    { label: "爆款帖子", value: statTotals.hot, color: "#CF1322" as string | undefined },
    { label: "含线索帖子", value: statTotals.withLeads, color: "#2F54EB" as string | undefined },
  ];

  return (
    <div style={{ maxWidth: 1440, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: "#1F1F1F" }}>帖子池</div>
          <div style={{ fontSize: 13, color: "#8C8C8C", marginTop: 2 }}>
            查看采集到的帖子内容，筛选爆款，一键跳转线索池
          </div>
        </div>
        <Space>
          {selectedRowKeys.length > 0 && (
            <Button
              type="primary"
              icon={<StarOutlined />}
              onClick={handleSaveToLibrary}
              loading={converting}
              size="small"
            >
              收藏到内容库 ({selectedRowKeys.length})
            </Button>
          )}
          <Button
            icon={<CloudDownloadOutlined />}
            onClick={() => void loadData(page, pageSize, filters)}
            size="small"
          >
            刷新
          </Button>
        </Space>
      </div>

      <Row gutter={[12, 8]} style={{ marginBottom: 16 }}>
        {statCards.map((s) => (
          <Col xs={8} sm={6} key={s.label}>
            <Card
              bodyStyle={{ padding: "12px 16px" }}
              style={{
                borderRadius: 8,
                border: s.color ? `1px solid ${s.color}33` : "1px solid #F0F0F0",
                background: s.color ? `${s.color}06` : "#fff",
              }}
            >
              <div style={{ fontSize: 12, color: "#8C8C8C", marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color || "#1F1F1F", lineHeight: 1.2 }}>
                {s.value}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card style={{ marginBottom: 12, borderRadius: 8 }} bodyStyle={{ padding: "12px 16px" }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={12} sm={6} md={4}>
            <select
              value={(filters.platform as string) ?? ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, platform: e.target.value }))}
              style={{ width: "100%", border: "1px solid #d9d9d9", borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
            >
              <option value="">全部平台</option>
              <option value="xhs">小红书</option>
              <option value="douyin">抖音</option>
              <option value="zhihu">知乎</option>
            </select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <select
              value={(filters.source_type as string) ?? ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, source_type: e.target.value }))}
              style={{ width: "100%", border: "1px solid #d9d9d9", borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
            >
              <option value="">全部来源</option>
              <option value="keyword">关键词</option>
              <option value="competitor_account">同行账号</option>
              <option value="manual_post">手动添加</option>
              <option value="hot_post_rule">爆款规则</option>
              <option value="xhs_library">内容库</option>
            </select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <select
              value={filters.is_hot === true ? "true" : filters.is_hot === false ? "false" : ""}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  is_hot: e.target.value === "true" ? true : e.target.value === "false" ? false : undefined,
                }))
              }
              style={{ width: "100%", border: "1px solid #d9d9d9", borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
            >
              <option value="">全部状态</option>
              <option value="true">爆款</option>
              <option value="false">非爆款</option>
            </select>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <input
              value={(filters.keyword as string) ?? ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, keyword: e.target.value }))}
              placeholder="搜索标题/内容/作者"
              style={{ width: "100%", border: "1px solid #d9d9d9", borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </Col>
          <Col>
            <Space>
              <Button type="primary" size="small" onClick={handleSearch} loading={loading}>
                查询
              </Button>
              <Button size="small" onClick={handleReset}>重置</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card style={{ borderRadius: 8 }} bodyStyle={{ padding: 0 }}>
        <Table
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ x: 1200 }}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => <Text type="secondary" style={{ fontSize: 12 }}>共 {t} 条</Text>,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
              void loadData(p, ps, filters);
            },
          }}
          onRow={(record) => ({
            onClick: () => handleViewDetail(record),
            style: {
              cursor: "pointer",
              background:
                highlightId && Number(highlightId) === record.id ? "#fff7e6" : undefined,
            },
          })}
        />
      </Card>

      <Drawer
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false);
          setDetailPost(null);
          setDetailLeads([]);
        }}
        width={580}
        title={
          detailPost ? (
            <Space>
              <Tag color="blue">{PLATFORM_LABELS[detailPost.platform] || detailPost.platform}</Tag>
              <span style={{ fontSize: 15, fontWeight: 600 }}>
                帖子 #{detailPost.id}
              </span>
              {detailPost.is_hot && <Tag color="red">爆款</Tag>}
            </Space>
          ) : (
            "帖子详情"
          )
        }
      >
        {detailPost && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div>
              <Text strong style={{ fontSize: 16 }}>
                {detailPost.title || "无标题"}
              </Text>
            </div>

            {detailPost.content && (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>内容</Text>
                <div style={{ background: "#fafafa", padding: 12, borderRadius: 8, marginTop: 4 }}>
                  <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 13 }}>
                    {detailPost.content}
                  </Paragraph>
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>来源</Text>
                <div style={{ marginTop: 4 }}>
                  <Tag>{SOURCE_TYPE_LABELS[detailPost.source_type] || detailPost.source_type}</Tag>
                </div>
              </div>
              {detailPost.author_name && (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>作者</Text>
                  <div style={{ marginTop: 4 }}>
                    <Text style={{ fontSize: 13 }}>{detailPost.author_name}</Text>
                    {detailPost.author_profile_url && (
                      <a
                        href={detailPost.author_profile_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ marginLeft: 6, fontSize: 12 }}
                      >
                        主页
                      </a>
                    )}
                  </div>
                </div>
              )}
              {detailPost.publish_time && (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>发布时间</Text>
                  <div style={{ marginTop: 4 }}>
                    <Text style={{ fontSize: 13 }}>{dayjs(detailPost.publish_time).format("YYYY-MM-DD HH:mm")}</Text>
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1F1F1F" }}>{detailPost.like_count}</div>
                <div style={{ fontSize: 12, color: "#8C8C8C" }}>点赞</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1F1F1F" }}>{detailPost.comment_count}</div>
                <div style={{ fontSize: 12, color: "#8C8C8C" }}>评论</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1F1F1F" }}>{detailPost.collect_count}</div>
                <div style={{ fontSize: 12, color: "#8C8C8C" }}>收藏</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: detailPost.lead_count > 0 ? "#2F54EB" : "#8C8C8C" }}>
                  {detailPost.lead_count}
                </div>
                <div style={{ fontSize: 12, color: "#8C8C8C" }}>线索</div>
              </div>
            </div>

            {detailPost.post_url && (
              <div>
                <a href={detailPost.post_url} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>
                  <LinkOutlined /> 查看原文链接
                </a>
              </div>
            )}

            <div>
              <Text strong style={{ fontSize: 14, display: "block", marginBottom: 12 }}>关联线索</Text>

              {detailLeadsLoading ? (
                <div style={{ textAlign: "center", padding: 24, color: "#8c8c8c" }}>加载中...</div>
              ) : detailLeads.length === 0 ? (
                <div style={{ textAlign: "center", padding: 24, color: "#8c8c8c" }}>
                  暂无线索，该帖子未产生线索
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {detailLeads.slice(0, 10).map((lead) => (
                    <div
                      key={lead.id}
                      style={{
                        border: "1px solid #f0f0f0",
                        borderRadius: 8,
                        padding: "10px 12px",
                        background: "#fafafa",
                        cursor: "pointer",
                      }}
                      onClick={() => navigate(`/leads?source_post_id=${detailPost.id}&source_comment_id=${lead.source_comment_id || ""}`)}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <Tag
                          color={LEAD_LEVEL_COLORS[lead.lead_level] || "default"}
                          style={{ margin: 0, fontSize: 11, fontWeight: 700 }}
                        >
                          {lead.lead_level}级
                        </Tag>
                        <Text style={{ fontSize: 12, fontWeight: 500 }}>{lead.user_name || "匿名"}</Text>
                        <Text type="secondary" style={{ fontSize: 11, marginLeft: "auto" }}>
                          评分 {lead.lead_score}
                        </Text>
                      </div>
                      <Text
                        ellipsis
                        style={{ fontSize: 12, color: "#595959", display: "block", maxWidth: "100%" }}
                      >
                        {lead.content || "-"}
                      </Text>
                      {lead.demand_type && (
                        <Tag color="purple" style={{ margin: 0, marginTop: 4, fontSize: 10 }}>
                          {lead.demand_type}
                        </Tag>
                      )}
                    </div>
                  ))}
                  {detailLeads.length > 10 && (
                    <Button
                      type="link"
                      size="small"
                      style={{ fontSize: 12 }}
                      onClick={() => navigate(`/leads?source_post_id=${detailPost.id}`)}
                    >
                      还有 {detailLeads.length - 10} 条线索，查看全部
                    </Button>
                  )}
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Button
                type="primary"
                icon={<StarOutlined />}
                onClick={async () => {
                  try {
                    const result = await convertPostsToNotes({ post_ids: [detailPost.id] });
                    showToast(
                      "success",
                      "收藏到内容库",
                      `成功 ${result.converted_count} 条，跳过 ${result.skipped_count} 条`,
                    );
                  } catch (err) {
                    message.error(err instanceof Error ? err.message : "收藏失败");
                  }
                }}
              >
                收藏到内容库
              </Button>
              <Button onClick={() => navigate(`/leads?source_post_id=${detailPost.id}`)}>
                查看关联线索
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
