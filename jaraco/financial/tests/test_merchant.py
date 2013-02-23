from jaraco.financial import merchant

class TestAgent():
	def test_two_instances_equal(self):
		agent1 = merchant.Agent('1', 'Henry')
		agent3 = merchant.Agent('1', 'Henry')
		assert agent1 == agent3
		d = {agent1: 'foo', agent3: 'bar'}
		assert len(d) == 1
