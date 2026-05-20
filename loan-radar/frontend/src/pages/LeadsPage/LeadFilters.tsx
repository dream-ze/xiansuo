import { Button, Col, Input, Row, Select, Space } from "antd";
import { RestOutlined, SearchOutlined } from "@ant-design/icons";
import type { LeadQueryParams } from "../../api";

const LEAD_LEVEL_OPTIONS = [
  { value: "", label: "全部" },
  { value: "A", label: "A级" },
  { value: "B", label: "B级" },
  { value: "C", label: "C级" },
  { value: "D", label: "D级" },
];

const PLATFORM_OPTIONS = [
  { value: "", label: "全部" },
  { value: "xhs", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];

const STATUS_OPTIONS = [
  { value: "", label: "全部" },
  { value: "new", label: "新线索" },
  { value: "contacted", label: "已跟进" },
  { value: "interested", label: "有意向" },
  { value: "invalid", label: "无效" },
  { value: "converted", label: "已转化" },
];

const DUPLICATE_OPTIONS = [
  { value: "", label: "全部" },
  { value: "false", label: "非重复线索" },
  { value: "true", label: "重复线索" },
];

const TIME_OPTIONS = [
  { value: "", label: "全部" },
  { value: "7", label: "最近7天" },
  { value: "15", label: "最近15天" },
  { value: "30", label: "最近30天" },
  { value: "90", label: "最近3个月" },
];

export type FilterValues = LeadQueryParams & { publish_time_days: string };

type Props = {
  filters: FilterValues;
  onChange: (filters: FilterValues) => void;
  onSearch: () => void;
  onReset: () => void;
  loading: boolean;
};

export default function LeadFilters({ filters, onChange, onSearch, onReset, loading }: Props) {
  function update(partial: Partial<FilterValues>) {
    onChange({ ...filters, ...partial });
  }

  return (
    <Row gutter={[12, 12]} align="middle">
      <Col xs={12} sm={8} md={6} lg={4}>
        <Select
          value={filters.lead_level || ""}
          onChange={(v) => update({ lead_level: v })}
          options={LEAD_LEVEL_OPTIONS}
          style={{ width: "100%" }}
          placeholder="线索等级"
        />
      </Col>
      <Col xs={12} sm={8} md={6} lg={4}>
        <Select
          value={filters.platform || ""}
          onChange={(v) => update({ platform: v })}
          options={PLATFORM_OPTIONS}
          style={{ width: "100%" }}
          placeholder="平台"
        />
      </Col>
      <Col xs={12} sm={8} md={6} lg={4}>
        <Select
          value={filters.status || ""}
          onChange={(v) => update({ status: v })}
          options={STATUS_OPTIONS}
          style={{ width: "100%" }}
          placeholder="状态"
        />
      </Col>
      <Col xs={12} sm={8} md={6} lg={4}>
        <Select
          value={filters.is_duplicate as string || ""}
          onChange={(v) => update({ is_duplicate: v })}
          options={DUPLICATE_OPTIONS}
          style={{ width: "100%" }}
          placeholder="重复筛选"
        />
      </Col>
      <Col xs={12} sm={8} md={6} lg={4}>
        <Select
          value={filters.publish_time_days || ""}
          onChange={(v) => update({ publish_time_days: v })}
          options={TIME_OPTIONS}
          style={{ width: "100%" }}
          placeholder="发布时间"
        />
      </Col>
      <Col xs={12} sm={8} md={6} lg={4}>
        <Input
          value={filters.demand_type || ""}
          onChange={(e) => update({ demand_type: e.target.value })}
          placeholder="需求类型"
          allowClear
        />
      </Col>
      <Col xs={24} sm={16} md={12} lg={8}>
        <Input
          value={filters.keyword || ""}
          onChange={(e) => update({ keyword: e.target.value })}
          placeholder="关键词搜索"
          allowClear
          onPressEnter={onSearch}
        />
      </Col>
      <Col>
        <Space>
          <Button type="primary" icon={<SearchOutlined />} onClick={onSearch} loading={loading}>查询</Button>
          <Button icon={<RestOutlined />} onClick={onReset}>重置</Button>
        </Space>
      </Col>
    </Row>
  );
}
