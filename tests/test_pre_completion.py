"""
Tests for PreCompletionChecklistMiddleware

Validates that the middleware catches common failure modes
before task completion.
"""

import pytest
from pre_completion import (
    PreCompletionChecklistMiddleware,
    CheckResult,
    ChecklistResult
)


class TestPreCompletionChecklistMiddleware:
    """Test suite for PreCompletionChecklistMiddleware"""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        return PreCompletionChecklistMiddleware()
    
    # ========================================
    # Context Sufficiency Tests
    # ========================================
    
    def test_context_sufficiency_missing_keys(self, middleware):
        """Test that missing context keys are detected"""
        task_context = {
            'task': 'Write a function'
            # Missing 'constraints' and 'acceptance_criteria'
        }
        agent_output = {'code': 'def foo(): pass'}
        
        result = middleware.check(task_context, agent_output)
        
        assert not result.all_passed
        assert any(
            r.check_name == 'context_sufficiency' and not r.passed
            for r in result.results
        )
    
    def test_context_sufficiency_all_keys_present(self, middleware):
        """Test that all context keys pass the check"""
        task_context = {
            'task': 'Write a function',
            'constraints': 'Must be pure function',
            'acceptance_criteria': 'Returns correct value'
        }
        agent_output = {'code': 'def foo(): return 42'}
        
        result = middleware.check(task_context, agent_output)
        
        context_check = next(
            r for r in result.results 
            if r.check_name == 'context_sufficiency'
        )
        assert context_check.passed
    
    # ========================================
    # Planning Completeness Tests
    # ========================================
    
    def test_planning_completeness_no_plan(self, middleware):
        """Test that missing plan triggers warning"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(): pass'}
        
        result = middleware.check(task_context, agent_output, plan=None)
        
        planning_check = next(
            r for r in result.results
            if r.check_name == 'planning_completeness'
        )
        assert not planning_check.passed
        assert planning_check.severity == 'warning'
    
    def test_planning_completeness_incomplete_plan(self, middleware):
        """Test that incomplete plan is detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(): pass'}
        plan = {'steps': ['step1']}  # Missing 'approach' and 'considerations'
        
        result = middleware.check(task_context, agent_output, plan)
        
        planning_check = next(
            r for r in result.results
            if r.check_name == 'planning_completeness'
        )
        assert not planning_check.passed
    
    def test_planning_completeness_complete_plan(self, middleware):
        """Test that complete plan passes"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(): pass'}
        plan = {
            'steps': ['step1', 'step2'],
            'approach': 'TDD',
            'considerations': ['performance']
        }
        
        result = middleware.check(task_context, agent_output, plan)
        
        planning_check = next(
            r for r in result.results
            if r.check_name == 'planning_completeness'
        )
        assert planning_check.passed
    
    # ========================================
    # Stub Code Detection Tests
    # ========================================
    
    def test_stub_code_detection_todo(self, middleware):
        """Test that TODO comments are detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo():\n    # TODO: implement\n    pass'}
        
        result = middleware.check(task_context, agent_output)
        
        stub_check = next(
            r for r in result.results
            if r.check_name == 'no_stub_code'
        )
        assert not stub_check.passed
        assert stub_check.severity == 'error'
    
    def test_stub_code_detection_fixme(self, middleware):
        """Test that FIXME comments are detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo():\n    # FIXME: broken\n    pass'}
        
        result = middleware.check(task_context, agent_output)
        
        stub_check = next(
            r for r in result.results
            if r.check_name == 'no_stub_code'
        )
        assert not stub_check.passed
    
    def test_stub_code_detection_not_implemented(self, middleware):
        """Test that NotImplementedError is detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo():\n    raise NotImplementedError'}
        
        result = middleware.check(task_context, agent_output)
        
        stub_check = next(
            r for r in result.results
            if r.check_name == 'no_stub_code'
        )
        assert not stub_check.passed
    
    def test_stub_code_detection_no_stubs(self, middleware):
        """Test that clean code passes"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo():\n    return 42'}
        
        result = middleware.check(task_context, agent_output)
        
        stub_check = next(
            r for r in result.results
            if r.check_name == 'no_stub_code'
        )
        assert stub_check.passed
    
    # ========================================
    # Error Handling Tests
    # ========================================
    
    def test_error_handling_no_error_handling(self, middleware):
        """Test that missing error handling is detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo():\n    return risky_operation()'}
        
        result = middleware.check(task_context, agent_output)
        
        error_check = next(
            r for r in result.results
            if r.check_name == 'error_handling'
        )
        assert not error_check.passed
        assert error_check.severity == 'warning'
    
    def test_error_handling_with_try_except(self, middleware):
        """Test that try/except passes"""
        task_context = {'task': 'test'}
        agent_output = {
            'code': 'def foo():\n    try:\n        return risky()\n    except:\n        return None'
        }
        
        result = middleware.check(task_context, agent_output)
        
        error_check = next(
            r for r in result.results
            if r.check_name == 'error_handling'
        )
        assert error_check.passed
    
    def test_error_handling_with_none_check(self, middleware):
        """Test that None checks pass"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(x):\n    if x is None:\n        return default\n    return process(x)'}
        
        result = middleware.check(task_context, agent_output)
        
        error_check = next(
            r for r in result.results
            if r.check_name == 'error_handling'
        )
        assert error_check.passed
    
    # ========================================
    # Test Coverage Tests
    # ========================================
    
    def test_test_coverage_no_tests(self, middleware):
        """Test that missing tests are detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(): pass', 'tests': ''}
        
        result = middleware.check(task_context, agent_output)
        
        test_check = next(
            r for r in result.results
            if r.check_name == 'test_coverage'
        )
        assert not test_check.passed
        assert test_check.severity == 'warning'
    
    def test_test_coverage_insufficient_tests(self, middleware):
        """Test that insufficient tests are detected"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(): pass', 'tests': 'test'}  # Too short
        
        result = middleware.check(task_context, agent_output)
        
        test_check = next(
            r for r in result.results
            if r.check_name == 'test_coverage'
        )
        assert not test_check.passed
    
    def test_test_coverage_no_assertions(self, middleware):
        """Test that tests without assertions are detected"""
        task_context = {'task': 'test'}
        agent_output = {
            'code': 'def foo(): pass',
            'tests': 'def test_foo():\n    foo()'  # No assertions
        }
        
        result = middleware.check(task_context, agent_output)
        
        test_check = next(
            r for r in result.results
            if r.check_name == 'test_coverage'
        )
        assert not test_check.passed
    
    def test_test_coverage_adequate(self, middleware):
        """Test that adequate test coverage passes"""
        task_context = {'task': 'test'}
        agent_output = {
            'code': 'def foo(): pass',
            'tests': 'def test_foo():\n    assert foo() == 42\n    assert foo() is not None'
        }
        
        result = middleware.check(task_context, agent_output)
        
        test_check = next(
            r for r in result.results
            if r.check_name == 'test_coverage'
        )
        assert test_check.passed
    
    # ========================================
    # Custom Checks Tests
    # ========================================
    
    def test_custom_check_integration(self):
        """Test that custom checks are integrated"""
        def custom_check(context, output, plan):
            return CheckResult(
                passed=True,
                check_name='custom',
                message='Custom check passed',
                severity='info'
            )
        
        middleware = PreCompletionChecklistMiddleware(custom_checks=[custom_check])
        task_context = {'task': 'test', 'constraints': [], 'acceptance_criteria': []}
        agent_output = {'code': 'def foo(): pass', 'tests': 'assert True'}
        
        result = middleware.check(task_context, agent_output)
        
        assert any(r.check_name == 'custom' for r in result.results)
    
    def test_custom_check_failure(self):
        """Test that custom check failures are captured"""
        def failing_check(context, output, plan):
            return CheckResult(
                passed=False,
                check_name='custom_fail',
                message='Custom check failed',
                severity='error'
            )
        
        middleware = PreCompletionChecklistMiddleware(custom_checks=[failing_check])
        task_context = {'task': 'test', 'constraints': [], 'acceptance_criteria': []}
        agent_output = {'code': 'def foo(): pass', 'tests': 'assert True'}
        
        result = middleware.check(task_context, agent_output)
        
        assert not result.all_passed
        assert any(
            r.check_name == 'custom_fail' and not r.passed
            for r in result.results
        )
    
    # ========================================
    # ChecklistResult Tests
    # ========================================
    
    def test_checklist_result_all_passed(self, middleware):
        """Test ChecklistResult.all_passed property"""
        task_context = {'task': 'test', 'constraints': [], 'acceptance_criteria': []}
        agent_output = {
            'code': 'def foo():\n    try:\n        return 42\n    except:\n        return None',
            'tests': 'assert foo() == 42'
        }
        plan = {'steps': [], 'approach': 'test', 'considerations': []}
        
        result = middleware.check(task_context, agent_output, plan)
        
        # Should pass most checks
        assert isinstance(result, ChecklistResult)
        assert len(result.results) > 0
    
    def test_checklist_result_failures(self, middleware):
        """Test ChecklistResult.failures property"""
        task_context = {'task': 'test'}  # Missing keys
        agent_output = {'code': '# TODO: implement\npass'}  # Has stub
        
        result = middleware.check(task_context, agent_output)
        
        assert len(result.failures) > 0
        assert all(not f.passed for f in result.failures)
    
    def test_checklist_result_errors(self, middleware):
        """Test ChecklistResult.errors property"""
        task_context = {'task': 'test', 'constraints': [], 'acceptance_criteria': []}
        agent_output = {'code': '# TODO: implement\npass', 'tests': 'assert True'}
        
        result = middleware.check(task_context, agent_output)
        
        # Stub code should be error-level
        assert len(result.errors) > 0
        assert all(e.severity == 'error' for e in result.errors)
    
    def test_checklist_result_warnings(self, middleware):
        """Test ChecklistResult.warnings property"""
        task_context = {'task': 'test', 'constraints': [], 'acceptance_criteria': []}
        agent_output = {'code': 'def foo(): pass', 'tests': ''}  # No tests
        
        result = middleware.check(task_context, agent_output)
        
        # Missing tests should be warning-level
        assert len(result.warnings) > 0
        assert all(w.severity == 'warning' for w in result.warnings)
    
    def test_checklist_result_summary(self, middleware):
        """Test ChecklistResult.summary() method"""
        task_context = {'task': 'test'}
        agent_output = {'code': 'def foo(): pass'}
        
        result = middleware.check(task_context, agent_output)
        summary = result.summary()
        
        assert 'Checklist Results' in summary
        assert str(len(result.results)) in summary
    
    # ========================================
    # Edge Cases
    # ========================================
    
    def test_empty_inputs(self, middleware):
        """Test handling of empty inputs"""
        result = middleware.check({}, {})
        
        assert not result.all_passed
        assert len(result.failures) > 0
    
    def test_malformed_plan(self, middleware):
        """Test handling of malformed plan"""
        task_context = {'task': 'test', 'constraints': [], 'acceptance_criteria': []}
        agent_output = {'code': 'def foo(): pass', 'tests': 'assert True'}
        plan = {'steps': None, 'approach': None}  # Malformed
        
        result = middleware.check(task_context, agent_output, plan)
        
        # Should handle gracefully
        assert isinstance(result, ChecklistResult)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
