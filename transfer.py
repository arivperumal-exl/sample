from databricks.sdk import WorkspaceClient

w = WorkspaceClient()  # picks up DATABRICKS_HOST/TOKEN from env or ~/.databrickscfg

space_id = "<your_genie_space_id>"

# Start a conversation and wait for the answer
result = w.genie.start_conversation_and_wait(
    space_id=space_id,
    content="What were total sales last month?"
)

for attachment in result.attachments:
    if attachment.text:
        print(attachment.text.content)
    if attachment.query:
        print(attachment.query.query)  # generated SQL, if you need it

# Follow-up in the same conversation (keeps context)
follow_up = w.genie.create_message_and_wait(
    space_id=space_id,
    conversation_id=result.conversation_id,
    content="Break that down by region"
)
