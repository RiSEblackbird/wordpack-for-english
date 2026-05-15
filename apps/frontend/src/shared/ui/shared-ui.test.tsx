import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';
import {
  Badge,
  Button,
  Card,
  CommandPalette,
  DataToolbar,
  Drawer,
  EmptyState,
  IconButton,
  InlineAction,
  Input,
  MiniWordCard,
  SearchBox,
  SegmentedControl,
  Select,
  ShelfChip,
  SidePeek,
  Skeleton,
  Switch,
  Tabs,
  Tag,
  Textarea,
  Tooltip,
} from './index';

describe('dictionary shared ui', () => {
  it('renders reusable controls with the expected accessible surface', () => {
    const onButtonClick = vi.fn();
    const onSegmentChange = vi.fn();

    render(
      <div>
        <Button variant="primary" onClick={onButtonClick}>保存</Button>
        <IconButton aria-label="閉じる" />
        <Card as="article">カード本文</Card>
        <Badge variant="accent">accent</Badge>
        <Tag>tag</Tag>
        <ShelfChip>shelf</ShelfChip>
        <SearchBox label="lemma検索" shortcut="/" placeholder="Search" />
        <SegmentedControl
          label="表示モード"
          value="list"
          options={[
            { value: 'list', label: 'List' },
            { value: 'graph', label: 'Graph' },
          ]}
          onChange={onSegmentChange}
        />
        <EmptyState>空です</EmptyState>
        <Skeleton data-testid="skeleton" style={{ minHeight: 24 }} />
        <InlineAction>詳細</InlineAction>
        <Input aria-label="棚名" />
        <Textarea aria-label="棚メモ" />
        <Select aria-label="色">
          <option>Sky</option>
        </Select>
        <Switch aria-label="即時生成" />
        <Drawer>drawer</Drawer>
        <SidePeek>side peek</SidePeek>
        <Tabs>tabs</Tabs>
        <Tooltip>tooltip</Tooltip>
        <DataToolbar>toolbar</DataToolbar>
        <MiniWordCard as="aside">mini card</MiniWordCard>
        <CommandPalette>palette</CommandPalette>
      </div>,
    );

    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    fireEvent.click(screen.getByRole('button', { name: 'Graph' }));

    expect(onButtonClick).toHaveBeenCalledTimes(1);
    expect(onSegmentChange).toHaveBeenCalledWith('graph');
    expect(screen.getByLabelText('lemma検索')).toHaveAttribute('type', 'search');
    expect(screen.getByRole('switch', { name: '即時生成' })).toHaveAttribute('type', 'checkbox');
    expect(screen.getByText('mini card')).toBeInTheDocument();
    expect(screen.getByTestId('skeleton')).toHaveAttribute('aria-hidden', 'true');
  });
});
