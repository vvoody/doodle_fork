Article:

SELECT ID, post_date_gmt, post_content, post_title, post_status, post_name, post_modified_gmt, comment_count
	FROM wp_posts
	WHERE (post_status = 'publish' or post_status = 'draft' or post_status = 'pending')
		AND post_type = 'post'


Comment:

SELECT comment_ID, comment_post_ID, comment_author_email, comment_date_gmt, comment_content
	FROM wp_comments
	WHERE comment_approved = 1
		AND comment_author_email != ''


User:

SELECT comment_author, comment_author_email, comment_author_url
	FROM wp_comments
	WHERE comment_approved = 1
		AND comment_author_email != ''
	GROUP BY comment_author_email
