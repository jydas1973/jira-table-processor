


import os
import json
import datetime
from jira.client import JIRA
import os
from dotenv import load_dotenv

load_dotenv()

class JiraIncrementalSync:
    def __init__(self, jira_options, token_auth, output_file='all_tickets.json', project='EXACSDBOPS'):
        """
        Initialize Jira Incremental Sync
        
        :param jira_options: Dictionary with Jira server options
        :param token_auth: Authentication token
        :param output_file: Path to output JSON file
        :param project: Jira project key to sync
        """
        self.jira = JIRA(options=jira_options, token_auth=token_auth)
        self.output_file = output_file
        self.project = project

    

    
        
    def clean_text(self, text):
        """
        Clean and format text, preserving newlines
        
        :param text: Input text to clean
        :return: Cleaned text
        """
        if text:
            return text.strip().replace('\r\n', '\n').replace('\t', ' ')
        return 'No content'
    
    
    
    def load_existing_data(self):
        """
        Load existing issues from JSON file
        
        :return: Dictionary of existing issues keyed by issue key
        """
        if not os.path.exists(self.output_file):
            return {}
        
        with open(self.output_file, 'r') as f:
            existing_data = json.load(f)
        
        # Convert list to dictionary for efficient lookup
        return {issue['key']: issue for issue in existing_data}
    
    def get_custom_field_value(self, issue, field_id):
        """
        Safely retrieve custom field value
        
        :param issue: Jira issue object
        :param field_id: Custom field ID
        :return: Cleaned field value or None
        """
        try:
            value = getattr(issue.fields, field_id)
            return self.clean_text(value) if value else None
        except:
            return None

    def extract_issue_data(self, singleIssue):
        """
        Extract comprehensive data for a single issue
        
        :param singleIssue: Jira issue object
        :return: Dictionary with issue details
        """
        reporter = singleIssue.fields.reporter.displayName if singleIssue.fields.reporter else 'Unknown Reporter'
        issue_data = {
            'key': singleIssue.key,
            'summary': self.clean_text(singleIssue.fields.summary),
            'reporter': reporter,
            'description': self.clean_text(singleIssue.fields.description),
            'resolution': singleIssue.fields.resolution.name if singleIssue.fields.resolution else None,
            'root_cause': self.get_custom_field_value(singleIssue, 'customfield_12602'),
            'created_at': self.get_custom_field_value(singleIssue, 'created'),
            'comments': []
        }
        
        # Retrieve and store comments
        if hasattr(singleIssue.fields, 'comment') and singleIssue.fields.comment.comments:
            comments = singleIssue.fields.comment.comments
            issue_data['comments'] = [
                {
                    'author': comment.author.displayName,
                    'body': self.clean_text(comment.body)
                } 
                for comment in comments
            ]
        
        return issue_data

    def is_issue_modified(self, existing_issue, new_issue):
        """
        Check if an issue has been modified
        
        :param existing_issue: Previously stored issue data
        :param new_issue: Current Jira issue
        :return: Boolean indicating if issue is modified
        """
        def safe_compare(existing_value, new_value):
            # Handle None cases and equivalents
            if existing_value is None and new_value is None:
                return False
            
            if existing_value == "No root cause provided" and new_value is None:
                return False
                
            # Handle Jira object attributes
            if isinstance(new_value, type) and hasattr(new_value, 'name'):
                new_value = new_value.name
            
            # Handle resolution field comparison
            if existing_value == "Unresolved" and new_value is None:
                return False
                
            # Convert to cleaned strings for comparison
            new_str = self.clean_text(str(new_value)) if new_value is not None else None
            existing_str = self.clean_text(str(existing_value)) if existing_value is not None else None
            
            # Special handling for "No content" and None equivalence
            if (existing_str == 'No content' and new_str is None) or \
            (existing_str is None and new_str == 'No content'):
                return False
                
            return existing_str != new_str

        # Comparison map for fields
        comparison_map = {
            'summary': new_issue.fields.summary,
            'description': new_issue.fields.description,
            'resolution': new_issue.fields.resolution,
            'root_cause': getattr(new_issue.fields, 'customfield_12602', None)
        }

        # Check if any key fields are modified
        for field, new_value in comparison_map.items():
            if safe_compare(existing_issue.get(field), new_value):
                print(f"Field '{field}' modified:")
                print(f"  Old value: {existing_issue.get(field)}")
                print(f"  New value: {new_value}")
                return True
        
        # Compare comments
        existing_comments = existing_issue.get('comments', [])
        new_comments = new_issue.fields.comment.comments if hasattr(new_issue.fields, 'comment') and new_issue.fields.comment else []
        
        # Filter out placeholder messages from existing comments
        existing_comments = [
            comment for comment in existing_comments 
            if not (isinstance(comment, dict) and comment.get('message') == 'No comments found for this issue.')
        ]
        
        # Check comment count
        if len(existing_comments) != len(new_comments):
            # Only consider it modified if there's an actual difference in real comments
            if len(existing_comments) > 0 or len(new_comments) > 0:
                print(f"Comment count changed: {len(existing_comments)} -> {len(new_comments)}")
                return True
        
        # Check comment content
        if new_comments:
            for old_comment, new_comment in zip(existing_comments, new_comments):
                if self.clean_text(old_comment.get('body', '')) != self.clean_text(new_comment.body):
                    print("Comment content modified")
                    return True
        
        return False
    
    def sync_jira_issues(self, batch_size=500, max_issues=11000):
        """
        Synchronize Jira issues, handling updates and new tickets
        
        :param batch_size: Number of issues to retrieve per batch
        :param max_issues: Maximum number of issues to retrieve
        """
        # Load existing data
        existing_issues = self.load_existing_data()
        updated_issues = list(existing_issues.values())
        
        # Retrieve issues in batches
        for start_at in range(0, max_issues, batch_size):
            print(f"Retrieving issues {start_at + 1} to {min(start_at + batch_size, max_issues)}...")
            
            # Construct JQL to get all issues from the project
            jql_str = f'project = {self.project}'
            
            batch = self.jira.search_issues(
                jql_str=jql_str,
                startAt=start_at,
                maxResults=batch_size
            )
            
            # Process each issue
            for singleIssue in batch:
                # Extract full issue data
                issue_data = self.extract_issue_data(singleIssue)
                
                # Check if issue exists and is modified
                if (singleIssue.key in existing_issues and 
                    self.is_issue_modified(existing_issues[singleIssue.key], singleIssue)):
                    # Replace existing issue
                    updated_issues = [
                        issue for issue in updated_issues if issue['key'] != singleIssue.key
                    ]
                    updated_issues.append(issue_data)
                    print(f"Updated issue: {singleIssue.key}")
                
                # Add new issues
                elif singleIssue.key not in existing_issues:
                    updated_issues.append(issue_data)
                    print(f"Added new issue: {singleIssue.key}")
        
        # Write updated data to file
        with open(self.output_file, 'w') as json_file:
            json.dump(updated_issues, json_file, indent=4)
        
        print(f"Data synchronization complete. Total issues: {len(updated_issues)}")

# Example usage
def main():
    # Jira server options (replace with your actual configuration)
    jira_options = {'server': "https://api.jira-sd.oci.oracleiaas.com"}
    
    # Initialize and run sync
    sync = JiraIncrementalSync(
        jira_options=jira_options, 
        token_auth= os.getenv("token_auth"),  # Replace with your actual token
        output_file='all_tickets_new.json',
        project='EXACSDBOPS'
    )
    sync.sync_jira_issues()
    
    sync = JiraIncrementalSync(
        jira_options=jira_options, 
        token_auth= os.getenv("token_auth"),  # Replace with your actual token
        output_file='all_tickets_new.json',
        project='EXACCDBOPS'
    )
    
    sync.sync_jira_issues()

if __name__ == '__main__':
    main()


