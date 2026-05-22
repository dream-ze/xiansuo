import httpx
import time

resp = httpx.post('http://127.0.0.1:8080/api/crawl-tasks', json={
    'platform': 'xhs',
    'source_type': 'keyword',
    'source_value': '车贷',
    'login_type': 'cookie',
    'enable_comments': True,
    'max_posts': 20,
    'headless': True,
}, timeout=120)
data = resp.json()
task_id = data.get('id')
print(f'Task ID: {task_id}')
print(f'Status: {data.get("status")}')

print('\n等待采集完成...')
for i in range(60):
    time.sleep(5)
    r = httpx.get(f'http://127.0.0.1:8080/api/crawl-tasks/{task_id}', timeout=10)
    task = r.json()
    status = task.get('status')
    print(f'  [{(i+1)*5}s] status={status}, posts={task.get("post_count",0)}, comments={task.get("comment_count",0)}')
    if status in ('success', 'failed'):
        print(f'\n最终结果: {task}')
        break

print('\n--- 采集日志 ---')
log_resp = httpx.get('http://127.0.0.1:8080/api/crawler/logs', timeout=10)
log_data = log_resp.json()
for l in log_data.get('logs', []):
    print(f"{l['timestamp']} [{l['level']}] {l['message']}")
