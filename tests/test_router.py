import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from route_task import route
class TestRouter(unittest.TestCase):
    def test_intents(self):
        cases=[
 ('帮我从宽泛方向形成可证伪科学问题','research-question'),('评价研究创新性和可行性','research-question'),('检索最新材料文献并找研究空白','deep-research'),('读取论文并提取方法参数','deep-research'),('做PRISMA系统综述','systematic-review'),('进行meta-analysis','systematic-review'),('设计整体技术路线','research-design'),('建立实验计算联合研究方案','research-design'),('做正交实验和响应面','experiment-design'),('计算样本量与统计功效','experiment-design'),('清洗数据并诊断异常值','data-analysis'),('进行ANOVA和回归诊断','data-analysis'),('做贝叶斯推断和不确定性分析','data-analysis'),('绘制论文多panel图','scientific-figure'),('制作机制图和图形摘要','scientific-figure'),('画RMSD和自由能景观','scientific-figure'),('写论文摘要和引言','scientific-writing'),('润色Discussion','scientific-writing'),('模拟同行审稿','peer-review'),('检查审稿回复是否完整','peer-review'),('生成技术报告','technical-report'),('整理领导汇报','technical-report'),('制定科研项目里程碑','project-management'),('建立风险登记和工作包','project-management'),('做专利地图和现有技术检索','patent-and-transfer'),('进行FTO初筛','patent-and-transfer'),('检查科研图像是否重复拼接','research-integrity'),('审核引用是否真正支持结论','research-integrity'),('生成实验SOP和样品编码','laboratory'),('分析仪器数据并记录QC','laboratory'),('用Gaussian优化分子','computation-handoff'),('用GROMACS做100ns MD','computation-handoff'),('用有限元分析热力耦合','computation-handoff'),('用OpenFOAM做非牛顿流','computation-handoff'),('使用Aspen做流程模拟','computation-handoff')]
        for text,want in cases:
            with self.subTest(text=text): self.assertEqual(route(text)['workflow'],want)
if __name__=='__main__': unittest.main()
